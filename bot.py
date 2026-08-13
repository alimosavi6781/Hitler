#!/usr/bin/env python3
"""ربات فارسی هشدار بازار ارز دیجیتال — بدون وابستگی خارجی.

اجرا:
    cp .env.example .env
    # BOT_TOKEN را در .env قرار دهید
    python3 bot.py

داده‌های بازار از API عمومی OKX و در صورت خطا Coinbase دریافت می‌شوند.
این نرم‌افزار ابزار تحلیلی/آموزشی است و تضمین سود یا توصیه قطعی معامله نیست.
"""

from __future__ import annotations

import html
import json
import logging
import math
import os
import re
import signal
import sqlite3
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.9+ has zoneinfo
    ZoneInfo = None  # type: ignore[assignment]


APP_NAME = "هشداربان بازار"
APP_VERSION = "1.0.0"
USER_AGENT = f"PersianCryptoAlertBot/{APP_VERSION}"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
POPULAR_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
SUPPORTED_INTERVALS = {"15m": 15 * 60_000, "1h": 60 * 60_000}
FA_DIGITS = str.maketrans("0123456789,.-", "۰۱۲۳۴۵۶۷۸۹٬٫−")
EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬٫−", "0123456789,.-")
SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,15}USDT$")

if ZoneInfo is not None:
    try:
        TEHRAN_TZ = ZoneInfo("Asia/Tehran")
    except Exception:  # pragma: no cover
        TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))
else:  # pragma: no cover
    TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

log = logging.getLogger("market_alert_bot")


# ---------------------------------------------------------------------------
# تنظیمات و ابزارهای عمومی
# ---------------------------------------------------------------------------


def load_env_file(path: str = ".env") -> None:
    """یک فایل ساده .env را بدون نیاز به python-dotenv بارگذاری می‌کند."""
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def parse_id_set(value: str) -> frozenset[int]:
    result: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            log.warning("شناسه نامعتبر در ALLOWED_CHAT_IDS نادیده گرفته شد: %s", part)
    return frozenset(result)


def normalize_symbol(value: str) -> str:
    text = value.strip().upper().replace("-", "").replace("/", "").replace(" ", "")
    aliases = {"BTC": "BTCUSDT", "XBT": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT"}
    text = aliases.get(text, text)
    if not SYMBOL_RE.fullmatch(text):
        raise ValueError("نماد باید مثل BTCUSDT یا SOLUSDT باشد.")
    return text


def parse_number(value: str) -> float:
    text = value.translate(EN_DIGITS).replace(",", "").replace("_", "").strip()
    number = float(text)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("عدد باید بزرگ‌تر از صفر باشد.")
    return number


def fa_number(value: float, decimals: Optional[int] = None) -> str:
    if decimals is None:
        if abs(value) >= 1000:
            decimals = 2
        elif abs(value) >= 1:
            decimals = 3
        else:
            decimals = 6
    text = f"{value:,.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.translate(FA_DIGITS)


def fa_int(value: int) -> str:
    return f"{value:,}".translate(FA_DIGITS)


def fa_percent(value: float) -> str:
    return (f"{value:.2f}%").translate(FA_DIGITS)


def tehran_time(timestamp_ms: Optional[int] = None) -> str:
    moment = datetime.now(tz=TEHRAN_TZ) if timestamp_ms is None else datetime.fromtimestamp(timestamp_ms / 1000, tz=TEHRAN_TZ)
    return moment.strftime("%Y/%m/%d - %H:%M").translate(FA_DIGITS)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def symbol_label(symbol: str) -> str:
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    labels = {"BTC": "بیت‌کوین", "ETH": "اتریوم", "SOL": "سولانا", "BNB": "بایننس‌کوین"}
    return f"{labels.get(base, base)} ({symbol})"


def chunks(text: str, size: int = 3900) -> Iterable[str]:
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        if cut < size // 2:
            cut = size
        yield text[:cut]
        text = text[cut:].lstrip("\n")
    if text:
        yield text


@dataclass(frozen=True)
class Config:
    token: str
    database_path: str
    check_interval: int
    poll_timeout: int
    http_timeout: int
    allowed_chat_ids: frozenset[int]
    default_symbols: tuple[str, ...]
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN تنظیم نشده است. فایل .env.example را به .env کپی و توکن جدید را وارد کنید.")
        if not re.fullmatch(r"\d{5,15}:[A-Za-z0-9_-]{20,}", token):
            raise RuntimeError("فرمت BOT_TOKEN درست نیست.")

        configured_symbols: list[str] = []
        for raw_symbol in os.getenv("DEFAULT_SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(","):
            try:
                symbol = normalize_symbol(raw_symbol)
            except ValueError:
                continue
            if symbol not in configured_symbols:
                configured_symbols.append(symbol)
        if not configured_symbols:
            configured_symbols = list(DEFAULT_SYMBOLS)

        return cls(
            token=token,
            database_path=os.getenv("DATABASE_PATH", "data/bot.db"),
            check_interval=env_int("CHECK_INTERVAL", 60, 30, 900),
            poll_timeout=env_int("POLL_TIMEOUT", 50, 5, 55),
            http_timeout=env_int("HTTP_TIMEOUT", 15, 5, 60),
            allowed_chat_ids=parse_id_set(os.getenv("ALLOWED_CHAT_IDS", "")),
            default_symbols=tuple(configured_symbols[:8]),
            port=env_int("PORT", 0, 0, 65535),
        )


# ---------------------------------------------------------------------------
# پایگاه داده
# ---------------------------------------------------------------------------


class Database:
    def __init__(self, path: str, default_symbols: Sequence[str]) -> None:
        self.path = path
        self.default_symbols = tuple(default_symbols)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: Optional[sqlite3.Connection] = None
        if path == ":memory:":
            self._memory_connection = self._new_connection()
        self.initialize()

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def connection(self) -> sqlite3.Connection:
        return self._memory_connection or self._new_connection()

    def _close(self, conn: sqlite3.Connection) -> None:
        if self._memory_connection is None:
            conn.close()

    def initialize(self) -> None:
        conn = self.connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    display_name TEXT NOT NULL DEFAULT '',
                    signals_enabled INTEGER NOT NULL DEFAULT 1,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS symbols (
                    chat_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, symbol),
                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('above', 'below')),
                    target REAL NOT NULL CHECK(target > 0),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    triggered_at TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_price_alerts_active
                    ON price_alerts(active, symbol);

                CREATE TABLE IF NOT EXISTS sent_signals (
                    chat_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    candle_time INTEGER NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, symbol, signal_type, candle_time)
                );

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
        finally:
            self._close(conn)

    def subscribe(self, chat_id: int, user_id: Optional[int], display_name: str) -> None:
        now = utc_now_iso()
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO chats(chat_id, user_id, display_name, active, created_at, updated_at)
                   VALUES (?, ?, ?, 1, ?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET
                     user_id=excluded.user_id, display_name=excluded.display_name,
                     active=1, updated_at=excluded.updated_at""",
                (chat_id, user_id, display_name[:200], now, now),
            )
            count = conn.execute("SELECT COUNT(*) FROM symbols WHERE chat_id=?", (chat_id,)).fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT OR IGNORE INTO symbols(chat_id, symbol, created_at) VALUES (?, ?, ?)",
                    ((chat_id, symbol, now) for symbol in self.default_symbols),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            self._close(conn)

    def deactivate_chat(self, chat_id: int) -> None:
        conn = self.connection()
        try:
            conn.execute("UPDATE chats SET active=0, updated_at=? WHERE chat_id=?", (utc_now_iso(), chat_id))
        finally:
            self._close(conn)

    def is_subscribed(self, chat_id: int) -> bool:
        conn = self.connection()
        try:
            row = conn.execute("SELECT active FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
            return bool(row and row[0])
        finally:
            self._close(conn)

    def toggle_signals(self, chat_id: int) -> bool:
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT signals_enabled FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
            enabled = not bool(row[0]) if row else True
            conn.execute(
                "UPDATE chats SET signals_enabled=?, updated_at=? WHERE chat_id=?",
                (int(enabled), utc_now_iso(), chat_id),
            )
            conn.execute("COMMIT")
            return enabled
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            self._close(conn)

    def signals_enabled(self, chat_id: int) -> bool:
        conn = self.connection()
        try:
            row = conn.execute("SELECT signals_enabled FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
            return bool(row and row[0])
        finally:
            self._close(conn)

    def symbols_for_chat(self, chat_id: int) -> list[str]:
        conn = self.connection()
        try:
            return [row[0] for row in conn.execute("SELECT symbol FROM symbols WHERE chat_id=? ORDER BY symbol", (chat_id,))]
        finally:
            self._close(conn)

    def add_symbol(self, chat_id: int, symbol: str) -> bool:
        conn = self.connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM symbols WHERE chat_id=?", (chat_id,)).fetchone()[0]
            if count >= 8:
                raise ValueError("حداکثر ۸ نماد می‌توانی داشته باشی.")
            cursor = conn.execute(
                "INSERT OR IGNORE INTO symbols(chat_id, symbol, created_at) VALUES (?, ?, ?)",
                (chat_id, symbol, utc_now_iso()),
            )
            return cursor.rowcount > 0
        finally:
            self._close(conn)

    def delete_symbol(self, chat_id: int, symbol: str) -> bool:
        conn = self.connection()
        try:
            cursor = conn.execute("DELETE FROM symbols WHERE chat_id=? AND symbol=?", (chat_id, symbol))
            return cursor.rowcount > 0
        finally:
            self._close(conn)

    def signal_recipients(self, symbol: str) -> list[int]:
        conn = self.connection()
        try:
            rows = conn.execute(
                """SELECT c.chat_id FROM chats c
                   JOIN symbols s ON s.chat_id=c.chat_id
                   WHERE c.active=1 AND c.signals_enabled=1 AND s.symbol=?""",
                (symbol,),
            )
            return [int(row[0]) for row in rows]
        finally:
            self._close(conn)

    def monitored_symbols(self) -> list[str]:
        conn = self.connection()
        try:
            rows = conn.execute(
                """SELECT DISTINCT symbol FROM (
                     SELECT s.symbol FROM symbols s JOIN chats c ON c.chat_id=s.chat_id
                       WHERE c.active=1 AND c.signals_enabled=1
                     UNION
                     SELECT p.symbol FROM price_alerts p JOIN chats c ON c.chat_id=p.chat_id
                       WHERE p.active=1 AND c.active=1
                   ) ORDER BY symbol"""
            )
            return [row[0] for row in rows]
        finally:
            self._close(conn)

    def create_alert(self, chat_id: int, symbol: str, direction: str, target: float) -> int:
        if direction not in {"above", "below"}:
            raise ValueError("جهت هشدار نامعتبر است.")
        conn = self.connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE chat_id=? AND active=1", (chat_id,)
            ).fetchone()[0]
            if count >= 20:
                raise ValueError("حداکثر ۲۰ هشدار فعال می‌توانی داشته باشی؛ اول یکی را حذف کن.")
            cursor = conn.execute(
                """INSERT INTO price_alerts(chat_id, symbol, direction, target, active, created_at)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (chat_id, symbol, direction, target, utc_now_iso()),
            )
            return int(cursor.lastrowid)
        finally:
            self._close(conn)

    def alerts_for_chat(self, chat_id: int, active_only: bool = True) -> list[sqlite3.Row]:
        conn = self.connection()
        try:
            sql = "SELECT id, symbol, direction, target, active, created_at FROM price_alerts WHERE chat_id=?"
            params: list[Any] = [chat_id]
            if active_only:
                sql += " AND active=1"
            sql += " ORDER BY id DESC"
            return list(conn.execute(sql, params).fetchall())
        finally:
            self._close(conn)

    def active_alerts_for_symbol(self, symbol: str) -> list[sqlite3.Row]:
        conn = self.connection()
        try:
            return list(
                conn.execute(
                    """SELECT p.id, p.chat_id, p.symbol, p.direction, p.target
                       FROM price_alerts p JOIN chats c ON c.chat_id=p.chat_id
                       WHERE p.symbol=? AND p.active=1 AND c.active=1""",
                    (symbol,),
                ).fetchall()
            )
        finally:
            self._close(conn)

    def trigger_alert(self, alert_id: int) -> bool:
        conn = self.connection()
        try:
            cursor = conn.execute(
                "UPDATE price_alerts SET active=0, triggered_at=? WHERE id=? AND active=1",
                (utc_now_iso(), alert_id),
            )
            return cursor.rowcount > 0
        finally:
            self._close(conn)

    def reactivate_alert(self, alert_id: int) -> None:
        conn = self.connection()
        try:
            conn.execute("UPDATE price_alerts SET active=1, triggered_at=NULL WHERE id=?", (alert_id,))
        finally:
            self._close(conn)

    def delete_alert(self, chat_id: int, alert_id: int) -> bool:
        conn = self.connection()
        try:
            cursor = conn.execute("DELETE FROM price_alerts WHERE chat_id=? AND id=?", (chat_id, alert_id))
            return cursor.rowcount > 0
        finally:
            self._close(conn)

    def claim_signal(
        self,
        chat_id: int,
        symbol: str,
        signal_type: str,
        candle_time: int,
        cooldown_ms: int = 0,
    ) -> bool:
        """سیگنال را اتمیک رزرو می‌کند و در بازه cooldown از ارسال پشت‌سرهم جلوگیری می‌کند."""
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if cooldown_ms > 0:
                row = conn.execute(
                    """SELECT MAX(candle_time) FROM sent_signals
                       WHERE chat_id=? AND symbol=? AND signal_type=?""",
                    (chat_id, symbol, signal_type),
                ).fetchone()
                previous_time = int(row[0]) if row and row[0] is not None else None
                if previous_time is not None and candle_time - previous_time < cooldown_ms:
                    conn.execute("ROLLBACK")
                    return False
            cursor = conn.execute(
                """INSERT OR IGNORE INTO sent_signals(chat_id, symbol, signal_type, candle_time, sent_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (chat_id, symbol, signal_type, candle_time, utc_now_iso()),
            )
            conn.execute("COMMIT")
            return cursor.rowcount > 0
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            self._close(conn)

    def release_signal(self, chat_id: int, symbol: str, signal_type: str, candle_time: int) -> None:
        conn = self.connection()
        try:
            conn.execute(
                "DELETE FROM sent_signals WHERE chat_id=? AND symbol=? AND signal_type=? AND candle_time=?",
                (chat_id, symbol, signal_type, candle_time),
            )
        finally:
            self._close(conn)

    def get_last_update_id(self) -> Optional[int]:
        conn = self.connection()
        try:
            row = conn.execute("SELECT value FROM meta WHERE key='last_update_id'").fetchone()
            return int(row[0]) if row else None
        finally:
            self._close(conn)

    def set_last_update_id(self, update_id: int) -> None:
        conn = self.connection()
        try:
            conn.execute(
                """INSERT INTO meta(key, value) VALUES ('last_update_id', ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (str(update_id),),
            )
        finally:
            self._close(conn)


# ---------------------------------------------------------------------------
# داده بازار و اندیکاتورها
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candle:
    start_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    complete: bool


@dataclass(frozen=True)
class CandleResult:
    candles: tuple[Candle, ...]
    source: str


class MarketDataError(RuntimeError):
    pass


def http_json(url: str, timeout: int) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise MarketDataError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MarketDataError(str(exc)) from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise MarketDataError("پاسخ JSON معتبر نبود.") from exc


class OKXProvider:
    name = "OKX"

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def candles(self, symbol: str, interval: str, limit: int = 200) -> CandleResult:
        instrument = f"{symbol[:-4]}-USDT"
        bar = {"15m": "15m", "1h": "1H"}[interval]
        query = urllib.parse.urlencode({"instId": instrument, "bar": bar, "limit": min(limit, 300)})
        payload = http_json(f"https://www.okx.com/api/v5/market/candles?{query}", self.timeout)
        if not isinstance(payload, dict) or payload.get("code") != "0" or not isinstance(payload.get("data"), list):
            raise MarketDataError(f"پاسخ نامعتبر OKX: {str(payload)[:200]}")
        parsed: list[Candle] = []
        for row in payload["data"]:
            try:
                parsed.append(
                    Candle(
                        start_ms=int(row[0]),
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        complete=str(row[8]) == "1",
                    )
                )
            except (IndexError, TypeError, ValueError):
                continue
        parsed.sort(key=lambda candle: candle.start_ms)
        if len(parsed) < 60:
            raise MarketDataError("تعداد کندل‌های OKX کافی نیست.")
        return CandleResult(tuple(parsed), self.name)


class CoinbaseProvider:
    name = "Coinbase"

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def candles(self, symbol: str, interval: str, limit: int = 200) -> CandleResult:
        # قیمت USD برای تحلیل USDT تقریب بسیار نزدیکی است و فقط هنگام خطای OKX استفاده می‌شود.
        product = f"{symbol[:-4]}-USD"
        granularity = {"15m": 900, "1h": 3600}[interval]
        query = urllib.parse.urlencode({"granularity": granularity})
        payload = http_json(
            f"https://api.exchange.coinbase.com/products/{urllib.parse.quote(product)}/candles?{query}",
            self.timeout,
        )
        if not isinstance(payload, list):
            raise MarketDataError(f"پاسخ نامعتبر Coinbase: {str(payload)[:200]}")
        now_ms = int(time.time() * 1000)
        duration_ms = SUPPORTED_INTERVALS[interval]
        parsed: list[Candle] = []
        for row in payload[: min(limit, 300)]:
            try:
                start_ms = int(row[0]) * 1000
                parsed.append(
                    Candle(
                        start_ms=start_ms,
                        low=float(row[1]),
                        high=float(row[2]),
                        open=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        complete=start_ms + duration_ms <= now_ms,
                    )
                )
            except (IndexError, TypeError, ValueError):
                continue
        parsed.sort(key=lambda candle: candle.start_ms)
        if len(parsed) < 60:
            raise MarketDataError("تعداد کندل‌های Coinbase کافی نیست یا نماد پشتیبانی نمی‌شود.")
        return CandleResult(tuple(parsed), self.name)


class MarketClient:
    def __init__(self, timeout: int, cache_seconds: int = 20) -> None:
        self.providers = (OKXProvider(timeout), CoinbaseProvider(timeout))
        self.cache_seconds = cache_seconds
        self._cache: dict[tuple[str, str], tuple[float, CandleResult]] = {}
        self._lock = threading.Lock()

    def get_candles(self, symbol: str, interval: str, force: bool = False) -> CandleResult:
        if interval not in SUPPORTED_INTERVALS:
            raise ValueError("تایم‌فریم پشتیبانی نمی‌شود.")
        key = (symbol, interval)
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and not force and now - cached[0] < self.cache_seconds:
                return cached[1]

        errors: list[str] = []
        for provider in self.providers:
            try:
                result = provider.candles(symbol, interval)
                with self._lock:
                    self._cache[key] = (time.monotonic(), result)
                return result
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                log.warning("دریافت %s %s از %s ناموفق: %s", symbol, interval, provider.name, exc)
        raise MarketDataError(" | ".join(errors))

    def current_price(self, symbol: str) -> tuple[float, str]:
        result = self.get_candles(symbol, "15m")
        return result.candles[-1].close, result.source


def ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    multiplier = 2.0 / (period + 1)
    result = [float(values[0])]
    for value in values[1:]:
        result.append((float(value) - result[-1]) * multiplier + result[-1])
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(values)
    if len(values) <= period:
        return result
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    def value(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + gain / loss)

    result[period] = value(average_gain, average_loss)
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        average_gain = (average_gain * (period - 1) + gain) / period
        average_loss = (average_loss * (period - 1) + loss) / period
        result[index] = value(average_gain, average_loss)
    return result


def macd(values: Sequence[float]) -> tuple[list[float], list[float], list[float]]:
    fast = ema(values, 12)
    slow = ema(values, 26)
    line = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
    signal_line = ema(line, 9)
    histogram = [line_value - signal_value for line_value, signal_value in zip(line, signal_line)]
    return line, signal_line, histogram


def atr(candles: Sequence[Candle], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(candles)
    if len(candles) <= period:
        return result
    true_ranges: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            current = candle.high - candle.low
        else:
            previous_close = candles[index - 1].close
            current = max(candle.high - candle.low, abs(candle.high - previous_close), abs(candle.low - previous_close))
        true_ranges.append(current)
    average = sum(true_ranges[1 : period + 1]) / period
    result[period] = average
    for index in range(period + 1, len(candles)):
        average = (average * (period - 1) + true_ranges[index]) / period
        result[index] = average
    return result


def closed_candles(candles: Sequence[Candle], interval: str, now_ms: Optional[int] = None) -> list[Candle]:
    current_ms = int(time.time() * 1000) if now_ms is None else now_ms
    duration = SUPPORTED_INTERVALS[interval]
    return [candle for candle in candles if candle.complete or candle.start_ms + duration <= current_ms]


@dataclass(frozen=True)
class Analysis:
    symbol: str
    action: str  # buy, weakness, watch, neutral
    score: int
    candle_time: int
    price: float
    rsi: float
    ema9: float
    ema21: float
    ema50: float
    macd_histogram: float
    volume_ratio: float
    atr: float
    higher_trend: str
    reasons: tuple[str, ...]
    entry_low: float
    entry_high: float
    stop: float
    target1: float
    target2: float
    source: str


def analyze_market(symbol: str, fast_result: CandleResult, higher_result: CandleResult) -> Analysis:
    fast_candles = closed_candles(fast_result.candles, "15m")
    higher_candles = closed_candles(higher_result.candles, "1h")
    if len(fast_candles) < 60 or len(higher_candles) < 60:
        raise MarketDataError("برای تحلیل حداقل ۶۰ کندل بسته لازم است.")

    fast_closes = [candle.close for candle in fast_candles]
    higher_closes = [candle.close for candle in higher_candles]
    fast_ema9, fast_ema21, fast_ema50 = ema(fast_closes, 9), ema(fast_closes, 21), ema(fast_closes, 50)
    higher_ema9, higher_ema21, higher_ema50 = ema(higher_closes, 9), ema(higher_closes, 21), ema(higher_closes, 50)
    rsi_values = rsi(fast_closes, 14)
    _, _, histogram = macd(fast_closes)
    atr_values = atr(fast_candles, 14)

    current_rsi = float(rsi_values[-1] if rsi_values[-1] is not None else 50.0)
    current_atr = float(atr_values[-1] if atr_values[-1] is not None else fast_closes[-1] * 0.01)
    price = fast_closes[-1]
    average_volume = sum(candle.volume for candle in fast_candles[-21:-1]) / 20
    volume_ratio = fast_candles[-1].volume / average_volume if average_volume > 0 else 1.0

    higher_up = higher_closes[-1] > higher_ema50[-1] and higher_ema9[-1] > higher_ema21[-1]
    higher_down = higher_closes[-1] < higher_ema50[-1] and higher_ema9[-1] < higher_ema21[-1]
    fast_up = fast_ema9[-1] > fast_ema21[-1] and price > fast_ema50[-1]
    cross_up = fast_ema9[-1] > fast_ema21[-1] and fast_ema9[-2] <= fast_ema21[-2]
    cross_down = fast_ema9[-1] < fast_ema21[-1] and fast_ema9[-2] >= fast_ema21[-2]
    previous_high = max(candle.high for candle in fast_candles[-21:-1])
    breakout = price > previous_high and volume_ratio >= 1.15
    pullback_recovery = fast_closes[-2] <= fast_ema9[-2] and price > fast_ema9[-1] and fast_up
    macd_positive = histogram[-1] > 0 and histogram[-1] >= histogram[-2]
    macd_negative = histogram[-1] < 0 and histogram[-1] <= histogram[-2]

    score = 0
    reasons: list[str] = []
    if higher_up:
        score += 2
        reasons.append("روند یک‌ساعته صعودی است")
    elif higher_down:
        score -= 2
        reasons.append("روند یک‌ساعته نزولی است")
    else:
        reasons.append("روند یک‌ساعته خنثی است")
    if fast_up:
        score += 1
        reasons.append("قیمت بالای EMAهای کوتاه‌مدت قرار دارد")
    else:
        score -= 1
    if cross_up:
        score += 2
        reasons.append("تقاطع صعودی EMA 9 و EMA 21 دیده شد")
    if cross_down:
        score -= 2
        reasons.append("تقاطع نزولی EMA 9 و EMA 21 دیده شد")
    if breakout:
        score += 2
        reasons.append("شکست سقف ۲۰ کندل با افزایش حجم تأیید شد")
    if pullback_recovery:
        score += 1
        reasons.append("بازگشت قیمت بعد از پولبک تأیید شد")
    if 50 <= current_rsi <= 68:
        score += 1
        reasons.append("RSI در محدوده مناسب روند صعودی است")
    elif current_rsi >= 72:
        score -= 2
        reasons.append("RSI وارد محدوده داغ/اشباع خرید شده")
    elif current_rsi < 42:
        score -= 1
        reasons.append("RSI ضعف مومنتوم را نشان می‌دهد")
    if macd_positive:
        score += 1
        reasons.append("مومنتوم MACD مثبت و رو به رشد است")
    elif macd_negative:
        score -= 1
        reasons.append("مومنتوم MACD منفی است")
    if volume_ratio >= 1.2:
        score += 1
        reasons.append("حجم از میانگین ۲۰ کندل بیشتر است")

    entry_event = cross_up or breakout or pullback_recovery
    if higher_up and fast_up and entry_event and score >= 6 and 48 <= current_rsi <= 72:
        action = "buy"
    elif cross_down and (higher_down or current_rsi < 45) and macd_negative:
        action = "weakness"
    elif higher_up and fast_up and score >= 4:
        action = "watch"
    else:
        action = "neutral"

    risk_distance = max(current_atr * 1.5, price * 0.006)
    # برای جلوگیری از حد غیرمنطقی در کندل‌های خبری، فاصله را در ۴٪ محدود می‌کنیم.
    risk_distance = min(risk_distance, price * 0.04)
    entry_low = max(0.0, price - current_atr * 0.20)
    entry_high = price + current_atr * 0.10
    stop = max(0.0, price - risk_distance)
    target1 = price + risk_distance * 1.5
    target2 = price + risk_distance * 2.5
    source = fast_result.source if fast_result.source == higher_result.source else f"{fast_result.source}/{higher_result.source}"

    return Analysis(
        symbol=symbol,
        action=action,
        score=max(-10, min(10, score)),
        candle_time=fast_candles[-1].start_ms,
        price=price,
        rsi=current_rsi,
        ema9=fast_ema9[-1],
        ema21=fast_ema21[-1],
        ema50=fast_ema50[-1],
        macd_histogram=histogram[-1],
        volume_ratio=volume_ratio,
        atr=current_atr,
        higher_trend="صعودی" if higher_up else "نزولی" if higher_down else "خنثی",
        reasons=tuple(reasons),
        entry_low=entry_low,
        entry_high=entry_high,
        stop=stop,
        target1=target1,
        target2=target2,
        source=source,
    )


def analysis_message(result: Analysis, automatic: bool = False) -> str:
    escaped_symbol = html.escape(result.symbol)
    if result.action == "buy":
        title = "🟢 <b>هشدار بررسی برای ورود خرید (اسپات)</b>"
        status = "چند تأیید هم‌زمان دیده شده؛ قبل از ورود، کندل و شرایط خودت را هم بررسی کن."
    elif result.action == "weakness":
        title = "🔴 <b>هشدار ضعف روند</b>"
        status = "اگر خرید باز داری، حد ضرر و خروج پله‌ای را دوباره بررسی کن. این پیام سیگنال فروش استقراضی نیست."
    elif result.action == "watch":
        title = "🟡 <b>زیر نظر؛ هنوز تأیید ورود کامل نیست</b>"
        status = "روند مثبت است اما ماشه ورود معتبر کامل نشده؛ فعلاً صبر بهتر از تعقیب قیمت است."
    else:
        title = "⚪️ <b>فعلاً موقعیت ورود تأییدشده‌ای نیست</b>"
        status = "شرایط لازم هم‌زمان نشده‌اند؛ عجله نکن و منتظر تأیید بعدی بمان."

    score_display = max(0, min(10, result.score))
    reason_lines = "\n".join(f"• {html.escape(reason)}" for reason in result.reasons[:5])
    lines = [
        title,
        f"🪙 <b>{html.escape(symbol_label(result.symbol))}</b>",
        f"💵 قیمت کندل بسته: <b>{fa_number(result.price)} USDT</b>",
        f"📊 امتیاز شرایط: <b>{fa_int(score_display)} از ۱۰</b>",
        f"🧭 روند ۱ ساعته: <b>{result.higher_trend}</b>",
        f"📈 RSI تایم ۱۵ دقیقه: <b>{fa_number(result.rsi, 1)}</b>",
        f"🔊 نسبت حجم به میانگین: <b>{fa_number(result.volume_ratio, 2)}×</b>",
        "",
        f"<b>نتیجه:</b> {status}",
    ]
    if result.action == "buy":
        lines.extend(
            [
                "",
                "<b>پلن نمونه با ریسک متوسط:</b>",
                f"• محدوده بررسی ورود: <b>{fa_number(result.entry_low)} تا {fa_number(result.entry_high)} USDT</b>",
                f"• حد بی‌اعتباری/ضرر: <b>{fa_number(result.stop)} USDT</b>",
                f"• هدف اول: <b>{fa_number(result.target1)} USDT</b>",
                f"• هدف دوم: <b>{fa_number(result.target2)} USDT</b>",
                "• ریسک پیشنهادی: حداکثر ۱٪ سرمایه در این معامله",
            ]
        )
    lines.extend(
        [
            "",
            "<b>دلایل مهم:</b>",
            reason_lines,
            "",
            f"🕒 کندل: {tehran_time(result.candle_time)} (تهران)",
            f"🔎 منبع: {html.escape(result.source)} | تایم‌فریم: ۱۵دقیقه + تأیید ۱ساعته",
            "",
            "⚠️ تحلیل الگوریتمی و آموزشی است، نه تضمین سود. بدون اهرم و با حد ضرر معامله کن.",
        ]
    )
    if automatic:
        lines.append("برای دیدن وضعیت تازه، دکمه «تحلیل الان» را بزن.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram Bot API
# ---------------------------------------------------------------------------


class TelegramError(RuntimeError):
    def __init__(self, description: str, error_code: int = 0, parameters: Optional[dict[str, Any]] = None) -> None:
        super().__init__(description)
        self.description = description
        self.error_code = error_code
        self.parameters = parameters or {}


class TelegramClient:
    def __init__(self, token: str, timeout: int) -> None:
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self.timeout = timeout

    def call(self, method: str, payload: Optional[dict[str, Any]] = None, timeout: Optional[int] = None) -> Any:
        data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + method,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout, context=context) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
                raise TelegramError(
                    parsed.get("description", f"Telegram HTTP {exc.code}"),
                    int(parsed.get("error_code", exc.code)),
                    parsed.get("parameters") or {},
                ) from exc
            except json.JSONDecodeError:
                raise TelegramError(f"Telegram HTTP {exc.code}: {body[:300]}", exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TelegramError(str(exc)) from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise TelegramError("پاسخ تلگرام JSON معتبر نبود.") from exc
        if not parsed.get("ok"):
            raise TelegramError(
                parsed.get("description", "خطای ناشناخته تلگرام"),
                int(parsed.get("error_code", 0)),
                parsed.get("parameters") or {},
            )
        return parsed.get("result")

    def get_me(self) -> dict[str, Any]:
        return self.call("getMe")

    def delete_webhook(self) -> None:
        self.call("deleteWebhook", {"drop_pending_updates": False})

    def get_updates(self, offset: Optional[int], poll_timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        return self.call("getUpdates", payload, timeout=poll_timeout + self.timeout)

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[dict[str, Any]] = None,
        disable_preview: bool = True,
    ) -> Any:
        result = None
        for index, part in enumerate(chunks(text)):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": part,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            }
            if index == 0 and reply_markup:
                payload["reply_markup"] = reply_markup
            result = self.call("sendMessage", payload)
        return result

    def answer_callback(self, callback_id: str, text: str = "", alert: bool = False) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_id, "show_alert": alert}
        if text:
            payload["text"] = text[:200]
        self.call("answerCallbackQuery", payload)


# ---------------------------------------------------------------------------
# منو و منطق پیام‌ها
# ---------------------------------------------------------------------------


def inline_keyboard(rows: Sequence[Sequence[tuple[str, str]]]) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in rows
        ]
    }


def main_menu(enabled: bool = True) -> dict[str, Any]:
    toggle_text = "🔕 خاموش‌کردن سیگنال" if enabled else "🔔 روشن‌کردن سیگنال"
    return inline_keyboard(
        [
            [("💵 قیمت‌ها", "menu:prices"), ("📊 تحلیل الان", "menu:analysis")],
            [("⏰ هشدار قیمت جدید", "menu:new_alert"), ("📋 هشدارهای من", "menu:alerts")],
            [("🪙 نمادهای من", "menu:symbols"), (toggle_text, "menu:toggle")],
            [("❓ راهنما", "menu:help")],
        ]
    )


def symbol_keyboard(prefix: str, include_cancel: bool = True) -> dict[str, Any]:
    rows: list[list[tuple[str, str]]] = []
    for index in range(0, len(POPULAR_SYMBOLS), 2):
        rows.append([(symbol, f"{prefix}:{symbol}") for symbol in POPULAR_SYMBOLS[index : index + 2]])
    if include_cancel:
        rows.append([("❌ انصراف", "menu:cancel")])
    return inline_keyboard(rows)


WELCOME_TEXT = """سلام! 👋

من <b>هشداربان بازار</b> هستم؛ بازار ارز دیجیتال را آنلاین بررسی می‌کنم و برای شرایط زیر پیام می‌فرستم:

• هشدار تحلیلی ورود احتمالی اسپات با تأیید تایم ۱۵ دقیقه و ۱ ساعت
• هشدار ضعف روند برای مدیریت معامله باز
• هشدار رسیدن قیمت به عدد دلخواه تو
• نمایش قیمت و تحلیل لحظه‌ای BTC، ETH و نمادهای انتخابی

تنظیم فعلی: <b>کوتاه‌مدت، ریسک متوسط، بدون اهرم</b>.
برای شروع یکی از دکمه‌ها را بزن.

⚠️ هیچ الگوریتمی سود را تضمین نمی‌کند. هر هشدار فقط دعوت به بررسی است؛ حتماً حد ضرر و مدیریت سرمایه داشته باش."""

HELP_TEXT = """<b>راهنمای ربات</b>

/start — عضویت و نمایش منو
/prices — قیمت نمادهای من
/analysis — تحلیل همه نمادها
/alert — ساخت هشدار قیمت
/alerts — هشدارهای فعال
/addsymbol SOLUSDT — افزودن نماد
/delsymbol SOLUSDT — حذف نماد
/symbols — فهرست نمادها
/risk — محاسبه اندازه معامله
/id — نمایش شناسه چت
/cancel — لغو عملیات جاری
/help — همین راهنما

<b>ساخت مستقیم هشدار:</b>
<code>/alert BTCUSDT 70000 above</code>
یعنی وقتی BTC به ۷۰٬۰۰۰ یا بالاتر رسید خبر بده.
برای پایین‌تر از قیمت از <code>below</code> استفاده کن.

<b>محاسبه مدیریت سرمایه:</b>
<code>/risk 1000 1 64000 63000</code>
به‌ترتیب: سرمایه دلاری، درصد ریسک، ورود و حد ضرر.

<b>منطق هشدار تحلیلی:</b>
EMA 9/21/50، RSI 14، MACD، ATR، حجم و شکست سقف ۲۰ کندل در تایم ۱۵ دقیقه بررسی می‌شود و روند ۱ ساعته باید تأیید بدهد. فقط بسته‌شدن کندل مبنای سیگنال است تا خطا کمتر شود.

⚠️ برای فیوچرز و اهرم طراحی نشده و توصیه قطعی خرید/فروش نیست."""


class BotApplication:
    def __init__(self, config: Config, database: Database, telegram: TelegramClient, market: MarketClient) -> None:
        self.config = config
        self.db = database
        self.telegram = telegram
        self.market = market
        self.states: dict[tuple[int, int], dict[str, Any]] = {}
        self.states_lock = threading.Lock()
        self.bot_username = ""

    def allowed(self, chat_id: int) -> bool:
        return not self.config.allowed_chat_ids or chat_id in self.config.allowed_chat_ids

    def safe_send(self, chat_id: int, text: str, reply_markup: Optional[dict[str, Any]] = None) -> bool:
        try:
            self.telegram.send_message(chat_id, text, reply_markup)
            return True
        except TelegramError as exc:
            log.error("ارسال پیام به %s ناموفق: %s", chat_id, exc)
            if exc.error_code in {400, 403} and any(
                phrase in exc.description.lower() for phrase in ("blocked", "chat not found", "deactivated", "kicked")
            ):
                self.db.deactivate_chat(chat_id)
            return False

    def subscribe_from_message(self, message: dict[str, Any]) -> None:
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        display_name = " ".join(
            part for part in (sender.get("first_name", ""), sender.get("last_name", "")) if part
        ) or chat.get("title", "")
        self.db.subscribe(int(chat["id"]), sender.get("id"), display_name)

    def handle_update(self, update: dict[str, Any]) -> None:
        if "message" in update:
            self.handle_message(update["message"])
        elif "callback_query" in update:
            self.handle_callback(update["callback_query"])

    def handle_message(self, message: dict[str, Any]) -> None:
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if "id" not in chat:
            return
        chat_id = int(chat["id"])
        user_id = int(sender.get("id", chat_id))
        text = (message.get("text") or "").strip()
        if not text:
            return

        if not self.allowed(chat_id):
            self.safe_send(chat_id, "⛔️ این ربات خصوصی است و شناسه این چت اجازه دسترسی ندارد.\nشناسه چت: <code>%s</code>" % chat_id)
            return

        if text.startswith("/"):
            self.subscribe_from_message(message)
            command, _, arguments = text.partition(" ")
            command = command.split("@", 1)[0].lower()
            self.handle_command(chat_id, user_id, command, arguments.strip())
            return

        if not self.db.is_subscribed(chat_id):
            self.subscribe_from_message(message)
        if self.handle_state(chat_id, user_id, text):
            return
        self.safe_send(chat_id, "دستور را متوجه نشدم؛ از دکمه‌های منو استفاده کن 👇", main_menu(self.db.signals_enabled(chat_id)))

    def handle_command(self, chat_id: int, user_id: int, command: str, arguments: str) -> None:
        if command == "/start":
            self.clear_state(chat_id, user_id)
            self.safe_send(chat_id, WELCOME_TEXT, main_menu(self.db.signals_enabled(chat_id)))
        elif command in {"/help", "/menu"}:
            self.safe_send(chat_id, HELP_TEXT, main_menu(self.db.signals_enabled(chat_id)))
        elif command in {"/prices", "/price"}:
            self.send_prices(chat_id)
        elif command in {"/analysis", "/signal", "/signals"}:
            self.send_analysis(chat_id)
        elif command == "/alert":
            if arguments:
                self.create_alert_from_command(chat_id, arguments)
            else:
                self.begin_alert(chat_id, user_id)
        elif command == "/alerts":
            self.send_alerts(chat_id)
        elif command == "/delalert":
            self.delete_alert_command(chat_id, arguments)
        elif command == "/addsymbol":
            self.add_symbol_command(chat_id, arguments)
        elif command == "/delsymbol":
            self.delete_symbol_command(chat_id, arguments)
        elif command == "/symbols":
            self.send_symbols(chat_id)
        elif command == "/risk":
            self.risk_command(chat_id, arguments)
        elif command == "/id":
            self.safe_send(chat_id, f"شناسه این چت: <code>{chat_id}</code>")
        elif command == "/cancel":
            self.clear_state(chat_id, user_id)
            self.safe_send(chat_id, "عملیات لغو شد ✅", main_menu(self.db.signals_enabled(chat_id)))
        else:
            self.safe_send(chat_id, "این دستور وجود ندارد. /help را بزن.", main_menu(self.db.signals_enabled(chat_id)))

    def handle_callback(self, callback: dict[str, Any]) -> None:
        callback_id = str(callback.get("id", ""))
        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        sender = callback.get("from") or {}
        if "id" not in chat:
            return
        chat_id = int(chat["id"])
        user_id = int(sender.get("id", chat_id))
        data = str(callback.get("data", ""))
        try:
            self.telegram.answer_callback(callback_id)
        except TelegramError:
            pass
        if not self.allowed(chat_id):
            return
        self.db.subscribe(chat_id, user_id, str(sender.get("first_name", "")))

        if data == "menu:prices":
            self.send_prices(chat_id)
        elif data == "menu:analysis":
            self.send_analysis(chat_id)
        elif data == "menu:new_alert":
            self.begin_alert(chat_id, user_id)
        elif data == "menu:alerts":
            self.send_alerts(chat_id)
        elif data == "menu:symbols":
            self.send_symbols(chat_id)
        elif data == "menu:toggle":
            enabled = self.db.toggle_signals(chat_id)
            status = "روشن شد 🔔" if enabled else "خاموش شد 🔕"
            self.safe_send(chat_id, f"هشدار تحلیلی خودکار {status}\nهشدارهای قیمت دلخواه همچنان فعال می‌مانند.", main_menu(enabled))
        elif data == "menu:help":
            self.safe_send(chat_id, HELP_TEXT, main_menu(self.db.signals_enabled(chat_id)))
        elif data == "menu:cancel":
            self.clear_state(chat_id, user_id)
            self.safe_send(chat_id, "عملیات لغو شد ✅", main_menu(self.db.signals_enabled(chat_id)))
        elif data.startswith("alert_symbol:"):
            symbol = data.split(":", 1)[1]
            self.set_state(chat_id, user_id, {"step": "alert_price", "symbol": symbol})
            self.safe_send(
                chat_id,
                f"قیمت هدف برای <b>{html.escape(symbol)}</b> را بفرست.\nمثال: <code>70000</code>",
                inline_keyboard([[("❌ انصراف", "menu:cancel")]]),
            )
        elif data.startswith("alert_direction:"):
            direction = data.split(":", 1)[1]
            state = self.get_state(chat_id, user_id)
            if state.get("step") != "alert_direction" or direction not in {"above", "below"}:
                self.safe_send(chat_id, "این درخواست منقضی شده؛ دوباره هشدار بساز.")
                return
            try:
                alert_id = self.db.create_alert(chat_id, state["symbol"], direction, float(state["target"]))
            except ValueError as exc:
                self.safe_send(chat_id, f"❌ {html.escape(str(exc))}")
                return
            self.clear_state(chat_id, user_id)
            direction_fa = "برسد یا بالاتر برود" if direction == "above" else "برسد یا پایین‌تر برود"
            self.safe_send(
                chat_id,
                f"✅ هشدار شماره <b>#{fa_int(alert_id)}</b> ساخته شد.\nوقتی {html.escape(state['symbol'])} به <b>{fa_number(float(state['target']))} USDT</b> {direction_fa} خبر می‌دهم.",
                main_menu(self.db.signals_enabled(chat_id)),
            )
        elif data.startswith("delete_alert:"):
            try:
                alert_id = int(data.split(":", 1)[1])
            except ValueError:
                return
            deleted = self.db.delete_alert(chat_id, alert_id)
            self.safe_send(chat_id, "هشدار حذف شد ✅" if deleted else "هشدار پیدا نشد.")

    def set_state(self, chat_id: int, user_id: int, state: dict[str, Any]) -> None:
        with self.states_lock:
            self.states[(chat_id, user_id)] = state

    def get_state(self, chat_id: int, user_id: int) -> dict[str, Any]:
        with self.states_lock:
            return dict(self.states.get((chat_id, user_id), {}))

    def clear_state(self, chat_id: int, user_id: int) -> None:
        with self.states_lock:
            self.states.pop((chat_id, user_id), None)

    def handle_state(self, chat_id: int, user_id: int, text: str) -> bool:
        state = self.get_state(chat_id, user_id)
        if not state:
            return False
        if state.get("step") == "alert_price":
            try:
                target = parse_number(text)
            except (ValueError, TypeError):
                self.safe_send(chat_id, "قیمت معتبر بفرست؛ مثلاً <code>70000</code> یا /cancel")
                return True
            state.update({"step": "alert_direction", "target": target})
            self.set_state(chat_id, user_id, state)
            self.safe_send(
                chat_id,
                f"هدف: <b>{fa_number(target)} USDT</b>\nدر کدام حالت پیام بفرستم؟",
                inline_keyboard(
                    [
                        [("📈 رسید یا بالاتر رفت", "alert_direction:above")],
                        [("📉 رسید یا پایین‌تر رفت", "alert_direction:below")],
                        [("❌ انصراف", "menu:cancel")],
                    ]
                ),
            )
            return True
        return False

    def begin_alert(self, chat_id: int, user_id: int) -> None:
        self.set_state(chat_id, user_id, {"step": "alert_symbol"})
        self.safe_send(chat_id, "برای کدام ارز هشدار قیمت بسازم؟", symbol_keyboard("alert_symbol"))

    def create_alert_from_command(self, chat_id: int, arguments: str) -> None:
        parts = arguments.split()
        if len(parts) != 3:
            self.safe_send(chat_id, "فرمت درست:\n<code>/alert BTCUSDT 70000 above</code>\nجهت: above یا below")
            return
        try:
            symbol = normalize_symbol(parts[0])
            target = parse_number(parts[1])
            direction_aliases = {
                "above": "above", "up": "above", "بالا": "above", "بالاتر": "above",
                "below": "below", "down": "below", "پایین": "below", "پایینتر": "below", "پایین‌تر": "below",
            }
            direction = direction_aliases.get(parts[2].lower())
            if direction is None:
                raise ValueError("جهت باید above یا below باشد.")
            alert_id = self.db.create_alert(chat_id, symbol, direction, target)
        except ValueError as exc:
            self.safe_send(chat_id, f"❌ {html.escape(str(exc))}")
            return
        direction_fa = "بالاتر" if direction == "above" else "پایین‌تر"
        self.safe_send(
            chat_id,
            f"✅ هشدار #{fa_int(alert_id)}: {html.escape(symbol)} در {fa_number(target)} USDT یا {direction_fa}.",
            main_menu(self.db.signals_enabled(chat_id)),
        )

    def send_alerts(self, chat_id: int) -> None:
        alerts = self.db.alerts_for_chat(chat_id)
        if not alerts:
            self.safe_send(chat_id, "هیچ هشدار قیمت فعالی نداری.", inline_keyboard([[("➕ ساخت هشدار", "menu:new_alert")]]))
            return
        lines = ["<b>هشدارهای قیمت فعال تو:</b>", ""]
        buttons: list[list[tuple[str, str]]] = []
        for row in alerts:
            direction = "↗️ بالاتر از" if row["direction"] == "above" else "↘️ پایین‌تر از"
            lines.append(f"#{fa_int(row['id'])} — <b>{html.escape(row['symbol'])}</b> {direction} {fa_number(row['target'])} USDT")
            buttons.append([(f"🗑 حذف #{row['id']}", f"delete_alert:{row['id']}")])
        buttons.append([("➕ هشدار جدید", "menu:new_alert")])
        self.safe_send(chat_id, "\n".join(lines), inline_keyboard(buttons))

    def delete_alert_command(self, chat_id: int, arguments: str) -> None:
        try:
            alert_id = int(arguments.strip().lstrip("#").translate(EN_DIGITS))
        except ValueError:
            self.safe_send(chat_id, "شماره هشدار را بنویس؛ مثلاً <code>/delalert 3</code>")
            return
        deleted = self.db.delete_alert(chat_id, alert_id)
        self.safe_send(chat_id, "هشدار حذف شد ✅" if deleted else "هشدار فعالی با این شماره پیدا نشد.")

    def add_symbol_command(self, chat_id: int, arguments: str) -> None:
        if not arguments:
            self.safe_send(chat_id, "نماد را هم بنویس؛ مثلاً <code>/addsymbol SOLUSDT</code>")
            return
        try:
            symbol = normalize_symbol(arguments)
            added = self.db.add_symbol(chat_id, symbol)
        except ValueError as exc:
            self.safe_send(chat_id, f"❌ {html.escape(str(exc))}")
            return
        self.safe_send(chat_id, f"{html.escape(symbol)} اضافه شد ✅" if added else "این نماد از قبل در فهرستت بود.")

    def delete_symbol_command(self, chat_id: int, arguments: str) -> None:
        try:
            symbol = normalize_symbol(arguments)
        except ValueError as exc:
            self.safe_send(chat_id, f"❌ {html.escape(str(exc))}")
            return
        deleted = self.db.delete_symbol(chat_id, symbol)
        self.safe_send(chat_id, f"{html.escape(symbol)} حذف شد ✅" if deleted else "این نماد در فهرستت نبود.")

    def send_symbols(self, chat_id: int) -> None:
        symbols = self.db.symbols_for_chat(chat_id)
        text = "<b>نمادهای زیر نظر:</b>\n" + ("\n".join(f"• {html.escape(symbol_label(s))}" for s in symbols) if symbols else "فهرست خالی است.")
        text += "\n\nافزودن: <code>/addsymbol SOLUSDT</code>\nحذف: <code>/delsymbol SOLUSDT</code>\nحداکثر ۸ نماد."
        self.safe_send(chat_id, text)

    def send_prices(self, chat_id: int) -> None:
        symbols = self.db.symbols_for_chat(chat_id)
        if not symbols:
            self.safe_send(chat_id, "اول یک نماد اضافه کن: <code>/addsymbol BTCUSDT</code>")
            return
        self.safe_send(chat_id, "⏳ در حال دریافت قیمت‌های آنلاین...")
        lines = ["<b>💵 قیمت لحظه‌ای ارزهای تو</b>", ""]
        sources: set[str] = set()
        for symbol in symbols:
            try:
                price, source = self.market.current_price(symbol)
                lines.append(f"• <b>{html.escape(symbol)}</b>: {fa_number(price)} USDT")
                sources.add(source)
            except MarketDataError:
                lines.append(f"• <b>{html.escape(symbol)}</b>: دریافت نشد ❌")
        lines.extend(["", f"🕒 {tehran_time()} (تهران)", f"منبع: {html.escape('/'.join(sorted(sources)) or 'ناموجود')}"])
        self.safe_send(chat_id, "\n".join(lines), main_menu(self.db.signals_enabled(chat_id)))

    def analyze_symbol(self, symbol: str) -> Analysis:
        fast = self.market.get_candles(symbol, "15m")
        higher = self.market.get_candles(symbol, "1h")
        return analyze_market(symbol, fast, higher)

    def send_analysis(self, chat_id: int) -> None:
        symbols = self.db.symbols_for_chat(chat_id)
        if not symbols:
            self.safe_send(chat_id, "اول یک نماد اضافه کن: <code>/addsymbol BTCUSDT</code>")
            return
        self.safe_send(chat_id, "⏳ کندل‌های ۱۵ دقیقه و ۱ ساعت را بررسی می‌کنم...")
        for symbol in symbols:
            try:
                result = self.analyze_symbol(symbol)
                self.safe_send(chat_id, analysis_message(result))
            except MarketDataError as exc:
                log.error("تحلیل دستی %s ناموفق: %s", symbol, exc)
                self.safe_send(chat_id, f"❌ فعلاً داده کافی برای تحلیل <b>{html.escape(symbol)}</b> دریافت نشد؛ چند دقیقه بعد دوباره امتحان کن.")
        self.safe_send(chat_id, "منوی اصلی 👇", main_menu(self.db.signals_enabled(chat_id)))

    def risk_command(self, chat_id: int, arguments: str) -> None:
        parts = arguments.split()
        if len(parts) != 4:
            self.safe_send(
                chat_id,
                "<b>محاسبه اندازه معامله</b>\nفرمت:\n<code>/risk سرمایه درصدریسک ورود حدضرر</code>\nمثال: <code>/risk 1000 1 64000 63000</code>",
            )
            return
        try:
            capital, risk_percent, entry, stop = (parse_number(part) for part in parts)
            if risk_percent > 10:
                raise ValueError("درصد ریسک باید حداکثر ۱۰ باشد (پیشنهاد: ۰٫۵ تا ۱).")
            distance = abs(entry - stop)
            if distance == 0:
                raise ValueError("ورود و حد ضرر نباید برابر باشند.")
            risk_amount = capital * risk_percent / 100
            quantity = risk_amount / distance
            position_value = quantity * entry
            if position_value > capital:
                position_value = capital
                quantity = capital / entry
                actual_risk = quantity * distance
            else:
                actual_risk = risk_amount
        except (ValueError, TypeError) as exc:
            self.safe_send(chat_id, f"❌ {html.escape(str(exc))}")
            return
        self.safe_send(
            chat_id,
            "\n".join(
                [
                    "<b>نتیجه مدیریت سرمایه (اسپات):</b>",
                    f"• سرمایه: {fa_number(capital)} USDT",
                    f"• زیان قابل‌قبول: حدود {fa_number(actual_risk)} USDT",
                    f"• حداکثر ارزش معامله: <b>{fa_number(position_value)} USDT</b>",
                    f"• مقدار ارز: <b>{fa_number(quantity, 8)}</b>",
                    "",
                    "⚠️ کارمزد و لغزش قیمت در این محاسبه لحاظ نشده. برای هر معامله بیشتر از ۱٪ سرمایه را ریسک نکن.",
                ]
            ),
        )


# ---------------------------------------------------------------------------
# پایش پس‌زمینه و سرویس سلامت
# ---------------------------------------------------------------------------


class PriceMonitor(threading.Thread):
    def __init__(self, app: BotApplication, stop_event: threading.Event) -> None:
        super().__init__(name="price-monitor", daemon=True)
        self.app = app
        self.stop_event = stop_event

    def run(self) -> None:
        log.info("پایشگر بازار با فاصله %s ثانیه شروع شد.", self.app.config.check_interval)
        # کمی صبر می‌کنیم تا حلقه تلگرام کاملاً آماده شود.
        if self.stop_event.wait(3):
            return
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                self.check_once()
            except Exception:
                log.exception("خطای پیش‌بینی‌نشده در پایش بازار")
            elapsed = time.monotonic() - started
            self.stop_event.wait(max(1.0, self.app.config.check_interval - elapsed))

    def check_once(self) -> None:
        symbols = self.app.db.monitored_symbols()
        for symbol in symbols:
            if self.stop_event.is_set():
                return
            try:
                fast = self.app.market.get_candles(symbol, "15m", force=True)
                current_price = fast.candles[-1].close
            except MarketDataError as exc:
                log.error("قیمت %s دریافت نشد: %s", symbol, exc)
                continue
            self.check_price_alerts(symbol, current_price)
            recipients = [
                chat_id
                for chat_id in self.app.db.signal_recipients(symbol)
                if self.app.allowed(chat_id)
            ]
            if not recipients:
                continue
            try:
                higher = self.app.market.get_candles(symbol, "1h", force=True)
                result = analyze_market(symbol, fast, higher)
            except MarketDataError as exc:
                log.error("تحلیل خودکار %s ناموفق: %s", symbol, exc)
                continue
            if result.action not in {"buy", "weakness"}:
                continue
            message = analysis_message(result, automatic=True)
            for chat_id in recipients:
                # حتی در شکست‌های پیاپی، برای هر نماد بیشتر از یک پیام در دو ساعت نمی‌فرستیم.
                claimed = self.app.db.claim_signal(
                    chat_id,
                    symbol,
                    result.action,
                    result.candle_time,
                    cooldown_ms=2 * 60 * 60_000,
                )
                if not claimed:
                    continue
                if not self.app.safe_send(chat_id, message, main_menu(True)):
                    self.app.db.release_signal(chat_id, symbol, result.action, result.candle_time)

    def check_price_alerts(self, symbol: str, current_price: float) -> None:
        for row in self.app.db.active_alerts_for_symbol(symbol):
            chat_id = int(row["chat_id"])
            # محدودیت ALLOWED_CHAT_IDS هم برای پیام ورودی و هم اعلان خودکار اعمال می‌شود.
            if not self.app.allowed(chat_id):
                continue
            reached = current_price >= row["target"] if row["direction"] == "above" else current_price <= row["target"]
            if not reached or not self.app.db.trigger_alert(int(row["id"])):
                continue
            direction_text = "رسید یا بالاتر رفت" if row["direction"] == "above" else "رسید یا پایین‌تر رفت"
            message = "\n".join(
                [
                    "⏰ <b>هشدار قیمت فعال شد</b>",
                    f"🪙 {html.escape(symbol_label(symbol))}",
                    f"قیمت فعلی: <b>{fa_number(current_price)} USDT</b>",
                    f"هدف تو: {fa_number(float(row['target']))} USDT — {direction_text}",
                    f"🕒 {tehran_time()} (تهران)",
                    "",
                    "این هشدار به‌تنهایی سیگنال ورود نیست؛ قبل از معامله تحلیل و حد ضرر را بررسی کن.",
                ]
            )
            if not self.app.safe_send(chat_id, message, main_menu(True)):
                self.app.db.reactivate_alert(int(row["id"]))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/health", "/healthz"}:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {"ok": True, "service": "persian-crypto-alert-bot", "version": APP_VERSION},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def start_health_server(port: int) -> Optional[ThreadingHTTPServer]:
    if not port:
        return None
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()
    log.info("سرویس سلامت روی پورت %s فعال شد.", port)
    return server


def configure_bot_commands(telegram: TelegramClient) -> None:
    commands = [
        {"command": "start", "description": "شروع و منوی اصلی"},
        {"command": "prices", "description": "قیمت لحظه‌ای ارزهای من"},
        {"command": "analysis", "description": "تحلیل تکنیکال همین حالا"},
        {"command": "alert", "description": "ساخت هشدار قیمت"},
        {"command": "alerts", "description": "هشدارهای قیمت فعال"},
        {"command": "symbols", "description": "مدیریت نمادها"},
        {"command": "risk", "description": "محاسبه اندازه معامله"},
        {"command": "help", "description": "راهنما"},
        {"command": "cancel", "description": "لغو عملیات"},
    ]
    try:
        telegram.call("setMyCommands", {"commands": commands, "language_code": "fa"})
    except TelegramError as exc:
        log.warning("ثبت منوی دستورات ناموفق بود: %s", exc)


def run() -> int:
    load_env_file()
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
    )
    try:
        config = Config.from_env()
    except RuntimeError as exc:
        print(f"خطای تنظیمات: {exc}")
        return 2

    db = Database(config.database_path, config.default_symbols)
    telegram = TelegramClient(config.token, config.http_timeout)
    market = MarketClient(config.http_timeout)
    app = BotApplication(config, db, telegram, market)
    stop_event = threading.Event()

    def request_stop(signum: int, frame: Any) -> None:
        del frame
        log.info("سیگنال توقف %s دریافت شد.", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    health_server = start_health_server(config.port)

    try:
        me = telegram.get_me()
        app.bot_username = str(me.get("username", ""))
        log.info("ربات @%s با موفقیت متصل شد.", app.bot_username)
        telegram.delete_webhook()
        configure_bot_commands(telegram)
    except TelegramError as exc:
        log.error("اتصال اولیه به تلگرام ناموفق بود: %s", exc)
        if health_server:
            health_server.shutdown()
        return 1

    monitor = PriceMonitor(app, stop_event)
    monitor.start()
    last_update_id = db.get_last_update_id()
    offset = last_update_id + 1 if last_update_id is not None else None
    backoff = 1.0

    try:
        while not stop_event.is_set():
            try:
                updates = telegram.get_updates(offset, config.poll_timeout)
                backoff = 1.0
                for update in updates:
                    update_id = int(update.get("update_id", 0))
                    try:
                        app.handle_update(update)
                    except Exception:
                        log.exception("پردازش آپدیت %s ناموفق بود.", update_id)
                    finally:
                        db.set_last_update_id(update_id)
                        offset = update_id + 1
            except TelegramError as exc:
                if stop_event.is_set():
                    break
                retry_after = float(exc.parameters.get("retry_after", 0) or 0)
                wait = max(retry_after, backoff)
                log.warning("ارتباط با تلگرام قطع شد (%s)؛ تلاش مجدد در %.0f ثانیه", exc, wait)
                stop_event.wait(wait)
                backoff = min(backoff * 2, 60.0)
    finally:
        stop_event.set()
        monitor.join(timeout=10)
        if health_server:
            health_server.shutdown()
            health_server.server_close()
        log.info("ربات متوقف شد.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

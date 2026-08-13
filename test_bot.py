import math
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import (
    SUPPORTED_INTERVALS,
    Analysis,
    Candle,
    CandleResult,
    CoinbaseProvider,
    Config,
    Database,
    BotApplication,
    OKXProvider,
    PriceMonitor,
    analyze_market,
    closed_candles,
    ema,
    normalize_symbol,
    parse_number,
    rsi,
)


class UtilityTests(unittest.TestCase):
    def test_normalize_symbol_and_aliases(self):
        self.assertEqual(normalize_symbol("btc"), "BTCUSDT")
        self.assertEqual(normalize_symbol("eth/usdt"), "ETHUSDT")
        self.assertEqual(normalize_symbol("SOL-USDT"), "SOLUSDT")
        with self.assertRaises(ValueError):
            normalize_symbol("BTCUSD")

    def test_parse_persian_number(self):
        self.assertEqual(parse_number("۷۰٬۰۰۰٫۵"), 70000.5)
        self.assertEqual(parse_number("1,234.25"), 1234.25)
        with self.assertRaises(ValueError):
            parse_number("۰")

    def test_indicators(self):
        values = list(range(1, 51))
        self.assertEqual(len(ema(values, 9)), len(values))
        self.assertGreater(ema(values, 9)[-1], ema(values, 21)[-1])
        self.assertAlmostEqual(rsi(values, 14)[-1], 100.0)


class ProviderParserTests(unittest.TestCase):
    def test_okx_fixture(self):
        # ۶۰ ردیف کافی برای عبور از اعتبارسنجی provider می‌سازیم.
        rows = []
        base = 1_780_000_000_000
        for index in range(60):
            rows.append(
                [
                    str(base + index * 900_000),
                    str(100 + index),
                    str(102 + index),
                    str(99 + index),
                    str(101 + index),
                    "25.5",
                    "0",
                    "0",
                    "1",
                ]
            )
        with patch("bot.http_json", return_value={"code": "0", "msg": "", "data": list(reversed(rows))}):
            result = OKXProvider(timeout=1).candles("BTCUSDT", "15m", 60)
        self.assertEqual(result.source, "OKX")
        self.assertEqual(len(result.candles), 60)
        self.assertLess(result.candles[0].start_ms, result.candles[-1].start_ms)
        self.assertEqual(result.candles[-1].close, 160.0)
        self.assertTrue(result.candles[-1].complete)

    def test_coinbase_fixture(self):
        rows = []
        base_seconds = int(time.time()) - 100_000
        for index in range(60):
            # Coinbase: time, low, high, open, close, volume
            rows.append([base_seconds - index * 900, 99, 102, 100, 101, 12.5])
        with patch("bot.http_json", return_value=rows):
            result = CoinbaseProvider(timeout=1).candles("BTCUSDT", "15m", 60)
        self.assertEqual(result.source, "Coinbase")
        self.assertEqual(len(result.candles), 60)
        self.assertEqual(result.candles[-1].close, 101.0)


class AnalysisTests(unittest.TestCase):
    @staticmethod
    def make_result(values, interval, final_volume=50.0):
        duration = SUPPORTED_INTERVALS[interval]
        base = 1_780_000_000_000
        candles = []
        for index, value in enumerate(values):
            volume = final_volume if index == len(values) - 1 else 50.0
            candles.append(
                Candle(
                    start_ms=base + index * duration,
                    open=value - 0.3,
                    high=value + 0.5,
                    low=value - 0.5,
                    close=value,
                    volume=volume,
                    complete=True,
                )
            )
        return CandleResult(tuple(candles), "fixture")

    def test_confirmed_buy_setup(self):
        higher = [80 + index * 0.5 + math.sin(index / 3) * 0.2 for index in range(100)]
        fast = [100 + index * 0.08 + math.sin(index * 0.7) * 1.5 for index in range(99)] + [110]
        result = analyze_market(
            "BTCUSDT",
            self.make_result(fast, "15m", final_volume=100.0),
            self.make_result(higher, "1h"),
        )
        self.assertEqual(result.action, "buy")
        self.assertGreaterEqual(result.score, 6)
        self.assertLess(result.stop, result.price)
        self.assertGreater(result.target1, result.price)
        self.assertGreater(result.target2, result.target1)

    def test_incomplete_latest_candle_is_ignored(self):
        now = int(time.time() * 1000)
        complete = Candle(now - 2_000_000, 100, 101, 99, 100, 10, True)
        incomplete = Candle(now - 100_000, 200, 201, 199, 200, 10, False)
        result = closed_candles([complete, incomplete], "15m", now_ms=now)
        self.assertEqual(result, [complete])


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tempdir.name) / "test.db")
        self.db = Database(self.path, ("BTCUSDT", "ETHUSDT"))
        self.db.subscribe(1234, 1234, "کاربر تست")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_default_symbols_and_toggle(self):
        self.assertEqual(self.db.symbols_for_chat(1234), ["BTCUSDT", "ETHUSDT"])
        self.assertFalse(self.db.toggle_signals(1234))
        self.assertTrue(self.db.toggle_signals(1234))

    def test_alert_lifecycle(self):
        alert_id = self.db.create_alert(1234, "BTCUSDT", "above", 70_000)
        self.assertEqual(len(self.db.active_alerts_for_symbol("BTCUSDT")), 1)
        self.assertTrue(self.db.trigger_alert(alert_id))
        self.assertFalse(self.db.trigger_alert(alert_id))
        self.assertEqual(self.db.active_alerts_for_symbol("BTCUSDT"), [])

    def test_signal_deduplication_and_cooldown(self):
        self.assertTrue(self.db.claim_signal(1234, "BTCUSDT", "buy", 123_456))
        self.assertFalse(self.db.claim_signal(1234, "BTCUSDT", "buy", 123_456))
        self.assertFalse(
            self.db.claim_signal(1234, "BTCUSDT", "buy", 124_000, cooldown_ms=1_000)
        )
        self.assertTrue(
            self.db.claim_signal(1234, "BTCUSDT", "buy", 125_000, cooldown_ms=1_000)
        )
        self.db.release_signal(1234, "BTCUSDT", "buy", 123_456)
        self.assertTrue(self.db.claim_signal(1234, "BTCUSDT", "buy", 123_456))

    def test_monthly_subscription_grant_extend_and_revoke(self):
        first_expiry = self.db.grant_subscription(5678, 30, granted_by=1234)
        self.assertTrue(self.db.has_active_subscription(5678))
        second_expiry = self.db.grant_subscription(5678, 10, granted_by=1234)
        first = time.mktime(time.strptime(first_expiry[:19], "%Y-%m-%dT%H:%M:%S"))
        second = time.mktime(time.strptime(second_expiry[:19], "%Y-%m-%dT%H:%M:%S"))
        self.assertAlmostEqual(second - first, 10 * 86_400, delta=2)
        self.assertEqual(len(self.db.active_subscriptions()), 1)
        self.assertTrue(self.db.revoke_subscription(5678))
        self.assertFalse(self.db.has_active_subscription(5678))
        self.assertFalse(self.db.revoke_subscription(5678))

    def test_subscription_access_is_bound_to_user_and_private_chat(self):
        config = Config(
            token="123456:abcdefghijklmnopqrstuvwxyz_123456",
            database_path=self.path,
            check_interval=60,
            poll_timeout=50,
            http_timeout=15,
            allowed_chat_ids=frozenset(),
            subscription_mode=True,
            admin_user_ids=frozenset({1234}),
            support_username="seller_test",
            default_symbols=("BTCUSDT", "ETHUSDT"),
            port=0,
        )
        app = BotApplication(config, self.db, object(), object())
        self.assertTrue(app.allowed(1234, 1234))  # مدیر
        self.assertFalse(app.allowed(5678, 5678))
        self.db.grant_subscription(5678, 30, granted_by=1234)
        self.assertTrue(app.allowed(5678, 5678))
        self.assertFalse(app.allowed(-100123, 5678))  # گروه حتی برای مشترک مجاز نیست
        self.assertFalse(app.allowed(9999, 9999))  # فرستادن لینک دسترسی ایجاد نمی‌کند

    def test_price_alert_is_sent_once(self):
        alert_id = self.db.create_alert(1234, "BTCUSDT", "above", 70_000)

        class FakeApp:
            def __init__(self, database):
                self.db = database
                self.sent = []

            def allowed(self, chat_id):
                return True

            def safe_send(self, chat_id, text, reply_markup=None):
                self.sent.append((chat_id, text, reply_markup))
                return True

        app = FakeApp(self.db)
        monitor = PriceMonitor(app, threading.Event())
        monitor.check_price_alerts("BTCUSDT", 70_001)
        monitor.check_price_alerts("BTCUSDT", 70_100)
        self.assertEqual(len(app.sent), 1)
        self.assertEqual(app.sent[0][0], 1234)
        self.assertIn("هشدار قیمت فعال شد", app.sent[0][1])
        self.assertEqual(self.db.active_alerts_for_symbol("BTCUSDT"), [])
        self.assertFalse(self.db.trigger_alert(alert_id))


if __name__ == "__main__":
    unittest.main(verbosity=2)

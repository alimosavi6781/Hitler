# -*- coding: utf-8 -*-
"""لایه دیتابیس SQLite — بدون وابستگی خارجی"""
import json
import sqlite3
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
GEN_DIR = BASE_DIR / "generated"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
GEN_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "insta.db"
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    price       TEXT DEFAULT '',
    emoji       TEXT DEFAULT '🛍️',
    image_path  TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS posts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL DEFAULT 'post',   -- post | story
    title        TEXT DEFAULT '',
    caption      TEXT DEFAULT '',
    hashtags     TEXT DEFAULT '',
    image_path   TEXT DEFAULT '',
    template     TEXT DEFAULT 'product',
    product_id   INTEGER,
    scheduled_at TEXT,                            -- ISO با منطقه زمانی تهران
    status       TEXT DEFAULT 'draft',            -- draft | ai_draft | scheduled | ready | published | failed
    ig_media_id  TEXT DEFAULT '',
    permalink    TEXT DEFAULT '',
    published_at TEXT,
    error        TEXT DEFAULT '',
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS metrics (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT UNIQUE,
    followers      INTEGER,
    following      INTEGER,
    media_count    INTEGER,
    reach          INTEGER,
    impressions    INTEGER,
    profile_views  INTEGER,
    likes          INTEGER,
    comments       INTEGER,
    engagement_rate REAL,
    source         TEXT DEFAULT 'manual'          -- manual | api
);
CREATE TABLE IF NOT EXISTS activity (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts  TEXT DEFAULT (datetime('now')),
    message TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    text  TEXT,
    done  INTEGER DEFAULT 0
);
"""


def conn():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db():
    with _lock, conn() as c:
        c.executescript(SCHEMA)
        # تنظیمات پیش‌فرض
        defaults = {
            "shop_name": "فروشگاه من",
            "shop_handle": "my.shop",
            "shop_tagline": "کیفیت را با ما تجربه کنید",
            "shop_phone": "",
            "cta": "برای سفارش دایرکت بده",
            "color1": "#7C3AED",
            "color2": "#4F46E5",
            "accent": "#FBBF24",
            "post_time": "20:00",
            "story_time": "12:00",
            "auto_generate_posts": "1",
            "auto_publish_stories": "1",
            "ig_access_token": "",
            "ig_user_id": "",
            "public_base_url": "",
            "seeded": "0",
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))


def get_setting(key, default=""):
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with _lock, conn() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def all_settings():
    with conn() as c:
        rows = c.execute("SELECT key,value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ---------- محصولات ----------
def add_product(name, description="", price="", emoji="🛍️", image_path=""):
    with _lock, conn() as c:
        cur = c.execute(
            "INSERT INTO products(name,description,price,emoji,image_path) VALUES(?,?,?,?,?)",
            (name, description, price, emoji, image_path),
        )
        return cur.lastrowid


def get_products():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM products ORDER BY id DESC")]


def get_product(pid):
    with conn() as c:
        r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def delete_product(pid):
    with _lock, conn() as c:
        c.execute("DELETE FROM products WHERE id=?", (pid,))


# ---------- پست‌ها ----------
def add_post(kind, title="", caption="", hashtags="", image_path="", template="product",
             product_id=None, scheduled_at=None, status="draft"):
    with _lock, conn() as c:
        cur = c.execute(
            "INSERT INTO posts(kind,title,caption,hashtags,image_path,template,product_id,scheduled_at,status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (kind, title, caption, hashtags, image_path, template, product_id, scheduled_at, status),
        )
        return cur.lastrowid


def get_post(pid):
    with conn() as c:
        r = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def get_posts(status=None, kind=None, limit=None):
    q = "SELECT * FROM posts"
    conds, args = [], []
    if status:
        conds.append("status IN (%s)" % ",".join("?" * len(status)))
        args += list(status)
    if kind:
        conds.append("kind=?")
        args.append(kind)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY COALESCE(scheduled_at, created_at) ASC"
    if limit:
        q += " LIMIT %d" % int(limit)
    with conn() as c:
        return [dict(r) for r in c.execute(q, args)]


def update_post(pid, **fields):
    allowed = {"kind", "title", "caption", "hashtags", "image_path", "template",
               "product_id", "scheduled_at", "status", "ig_media_id", "permalink",
               "published_at", "error"}
    sets, args = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            args.append(v)
    if not sets:
        return
    args.append(pid)
    with _lock, conn() as c:
        c.execute(f"UPDATE posts SET {','.join(sets)} WHERE id=?", args)


def delete_post(pid):
    with _lock, conn() as c:
        c.execute("DELETE FROM posts WHERE id=?", (pid,))


def due_posts(now_iso):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM posts WHERE status='scheduled' AND scheduled_at IS NOT NULL "
            "AND scheduled_at <= ? ORDER BY scheduled_at",
            (now_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


def posts_today(date_prefix):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM posts WHERE scheduled_at LIKE ? OR published_at LIKE ?",
            (date_prefix + "%", date_prefix + "%"),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- متریک‌ها ----------
def upsert_metric(date, **fields):
    cols = list(fields.keys())
    with _lock, conn() as c:
        placeholders = ",".join(f"{k}=excluded.{k}" for k in cols)
        c.execute(
            f"INSERT INTO metrics(date,{','.join(cols)}) VALUES(?,{','.join('?'*len(cols))}) "
            f"ON CONFLICT(date) DO UPDATE SET {placeholders}",
            [date] + list(fields.values()),
        )


def get_metrics(limit=60):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM metrics ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ---------- فعالیت و تسک‌ها ----------
def log_activity(message):
    with _lock, conn() as c:
        c.execute("INSERT INTO activity(message) VALUES(?)", (message,))


def get_activity(limit=15):
    with conn() as c:
        rows = c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_tasks():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tasks ORDER BY id")]


def add_task(text):
    with _lock, conn() as c:
        return c.execute("INSERT INTO tasks(text) VALUES(?)", (text,)).lastrowid


def toggle_task(tid, done):
    with _lock, conn() as c:
        c.execute("UPDATE tasks SET done=? WHERE id=?", (1 if done else 0, tid))


def delete_task(tid):
    with _lock, conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (tid,))


def seed_default_tasks():
    tips = [
        "پروفایل پیج را کامل کن: بیو، لینک، اطلاعات تماس و هایلایت‌ها",
        "روزانه حداقل ۳ استوری منتشر کن (محصول، پشت‌صحنه، نظر مشتری)",
        "در یک ساعت اول بعد از هر پست، به همه کامنت‌ها جواب بده",
        "هایلایت‌های پیج را دسته‌بندی کن (محصولات، نظرات، ارسال و...)",
        "از ریپورت‌های پیج در تب آنالیز، بهترین ساعت انتشار را پیدا کن",
        "هفته‌ای یک ریلز (ویدیو کوتاه ۱۵ تا ۳۰ ثانیه‌ای) منتشر کن",
        "برای هر محصول از مشتری‌ها نظر و فیدبک واقعی بگیر و منتشر کن",
        "در کپشن‌ها سوال بپرس تا کامنت بگیر (مثلاً: شما کدوم رنگ رو می‌پسندید؟)",
        "با پیج‌های هم‌صنف یا پیج‌های محلی همکاری و تبادل تبلیغ کن",
        "روزهای تخفیف ویژه (مناسبت‌ها) را از قبل زمان‌بندی و استوری‌اش را آماده کن",
    ]
    with conn() as c:
        count = c.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"]
    if count == 0:
        for t in tips:
            add_task(t)

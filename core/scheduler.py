# -*- coding: utf-8 -*-
"""زمان‌بند: انتشار خودکار پست/استوری، تولید محتوای روزانه و جمع‌آوری اینسایت"""
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db
from .content import (generate_caption, random_quote, random_question,
                      random_tip, make_hashtags)
from .images import PostRenderer
from .ig_api import IGClient, IGError

TEHRAN = ZoneInfo("Asia/Tehran")
_scheduler = None


def now_tehran():
    return datetime.now(TEHRAN)


def now_iso():
    return now_tehran().isoformat(timespec="seconds")


def render_path(kind, uid):
    return str(Path(db.GEN_DIR) / f"{kind}_{uid}.jpg")


def build_caption_text(post):
    cap = (post.get("caption") or "").strip()
    tags = (post.get("hashtags") or "").strip()
    if tags and tags not in cap:
        cap = (cap + "\n\n" + tags).strip()
    return cap


def publish_post(post_id):
    """انتشار یک پست زمان‌بندی‌شده از طریق Graph API"""
    post = db.get_post(post_id)
    if not post:
        return
    token = db.get_setting("ig_access_token")
    ig_id = db.get_setting("ig_user_id")
    base = db.get_setting("public_base_url")
    if not (token and ig_id):
        db.update_post(post_id, status="ready")
        db.log_activity(f"⚠️ پست «{post['title']}» به دلیل نبود اتصال API به حالت «آماده انتشار دستی» رفت.")
        return

    fname = Path(post["image_path"]).name if post.get("image_path") else ""
    if not base or not fname:
        db.update_post(post_id, status="failed", error="آدرس عمومی سرور یا تصویر موجود نیست")
        return

    image_url = f"{base}/generated/{fname}"
    ig = IGClient(token, ig_id, base)
    try:
        mid, permalink = ig.publish(image_url, build_caption_text(post),
                                    is_story=(post["kind"] == "story"))
        db.update_post(post_id, status="published", ig_media_id=mid or "",
                       permalink=permalink or "", published_at=now_iso(), error="")
        kind = "استوری" if post["kind"] == "story" else "پست"
        db.log_activity(f"✅ {kind} «{post['title']}» به‌صورت خودکار در اینستاگرام منتشر شد.")
        return True
    except IGError as e:
        db.update_post(post_id, status="failed", error=str(e)[:500])
        db.log_activity(f"❌ انتشار «{post['title']}» ناموفق بود: {e}")
        return False


def check_due():
    """بررسی پست‌های سررسیدشده — هر دقیقه اجرا می‌شود"""
    due = db.due_posts(now_iso())
    for p in due:
        publish_post(p["id"])


def _least_recent_product():
    products = db.get_products()
    if not products:
        return None
    recent = db.get_posts(status=["published", "scheduled", "ai_draft", "ready", "failed"])[:40]
    used = {}
    for p in recent:
        if p.get("product_id") and p["product_id"] not in used:
            used[p["product_id"]] = True
    unused = [p for p in products if p["id"] not in used]
    pool = unused or products
    return random.choice(pool)


def _shop_dict():
    s = db.all_settings()
    return {
        "name": s.get("shop_name", "فروشگاه من"),
        "handle": s.get("shop_handle", ""),
        "phone": s.get("shop_phone", s.get("phone", "")),
        "tagline": s.get("shop_tagline", ""),
        "cta": s.get("cta", "برای سفارش دایرکت بده"),
        "color1": s.get("color1", "#7C3AED"),
        "color2": s.get("color2", "#4F46E5"),
        "accent": s.get("accent", "#FBBF24"),
    }


def create_post_ai(scheduled_date_iso):
    """ساخت پست هوشمند روزانه (پیش‌نویس نیازمند تأیید)"""
    product = _least_recent_product()
    shop = _shop_dict()
    tpl = random.choices(["intro", "intro", "question", "offer"], weights=[4, 4, 2, 1])[0]
    if product:
        title = product["name"]
        desc = product["description"]
        price = product["price"]
    else:
        title = "محصول ویژه امروز"
        desc = random_tip()
        price = ""
    caption, tags = generate_caption("post", tpl, shop=shop["name"], product=title,
                                     desc=desc, price=price, cta=shop["cta"])
    uid = datetime.now().strftime("%Y%m%d%H%M%S")
    path = render_path("post", uid)
    PostRenderer(shop).render(kind="post", template=tpl,
                              product={"name": title, "description": desc,
                                       "price": price,
                                       "image_path": product["image_path"] if product else "",
                                       "emoji": product["emoji"] if product else "tag"},
                              title=title, text=(desc if tpl != "offer" else ""),
                              price=price,
                              extra="پیشنهاد ویژه" if tpl == "offer" else "",
                              out_path=path)
    return db.add_post("post", title=title, caption=caption, hashtags=" ".join(tags),
                       image_path=path, template=tpl,
                       product_id=product["id"] if product else None,
                       scheduled_at=scheduled_date_iso, status="ai_draft")


def create_story_ai(scheduled_date_iso, product=None):
    """ساخت استوری روزانه — مستقیم زمان‌بندی می‌شود"""
    shop = _shop_dict()
    product = product or _least_recent_product()
    tpl = random.choice(["product", "product", "tip", "quote", "question"])
    extra, desc, price, title = "", "", "", "استوری امروز"
    if tpl == "product" and product:
        title = product["name"]
        desc = product["description"]
        price = product["price"]
        caption, tags = generate_caption("story", shop=shop["name"], product=title,
                                         desc=desc, price=price, cta=shop["cta"])
    else:
        if tpl == "tip":
            extra = random_tip()
        elif tpl == "quote":
            extra = random_quote()
        else:
            extra = random_question()
        title = {"tip": "نکته روز", "quote": "جمله امروز", "question": "سوال امروز"}.get(tpl, "استوری")
        caption = extra
        tags = make_hashtags(shop["name"])
    uid = datetime.now().strftime("%Y%m%d%H%M%S")
    path = render_path("story", uid)
    PostRenderer(shop).render(kind="story", template=tpl,
                              product={"name": title, "description": desc,
                                       "price": price,
                                       "image_path": product["image_path"] if product else "",
                                       "emoji": product["emoji"] if product else "tag"},
                              title=title, text=desc, price=price, extra=extra,
                              icon="bulb" if tpl == "tip" else "heart",
                              out_path=path)
    return db.add_post("story", title=title, caption=caption, hashtags=" ".join(tags),
                       image_path=path, template=tpl,
                       product_id=product["id"] if product else None,
                       scheduled_at=scheduled_date_iso, status="scheduled")


def daily_generate():
    """هر روز ساعت ۰۹:۰۰ — تولید پست و استوری‌های امروز"""
    today = now_tehran()
    date = today.strftime("%Y-%m-%d")
    settings = db.all_settings()

    if settings.get("auto_publish_stories") == "1":
        for time_str, slot in (("story_time", "اول"), ("story_time_2", "دوم")):
            t = settings.get(time_str) or ("12:00" if slot == "اول" else "21:00")
            iso = f"{date}T{t}:00+03:30"
            existing = [p for p in db.get_posts(status=["scheduled", "ai_draft", "published"])
                        if p["kind"] == "story" and (p.get("scheduled_at") or "").startswith(iso[:16])]
            if not existing:
                create_story_ai(iso)
                db.log_activity(f"📱 استوری {slot} امروز به‌صورت خودکار ساخته و زمان‌بندی شد ({t}).")

    if settings.get("auto_generate_posts") == "1":
        t = settings.get("post_time") or "20:00"
        iso = f"{date}T{t}:00+03:30"
        existing = [p for p in db.get_posts(status=["ai_draft", "scheduled", "published"])
                    if p["kind"] == "post" and (p.get("scheduled_at") or "").startswith(iso[:16])]
        if not existing:
            create_post_ai(iso)
            db.log_activity(f"🤖 پست پیشنهادی امروز ساخته شد و منتظر تأیید توست (انتشار {t}).")


def daily_insights():
    token = db.get_setting("ig_access_token")
    ig_id = db.get_setting("ig_user_id")
    if token and ig_id:
        try:
            from .analytics import fetch_and_store
            fetch_and_store(token, ig_id)
        except Exception as e:
            db.log_activity(f"⚠️ جمع‌آوری اینسایت ناموفق بود: {e}")


def start():
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone=TEHRAN)
    _scheduler.add_job(check_due, "interval", minutes=1, id="check_due", max_instances=1)
    _scheduler.add_job(daily_generate, CronTrigger(hour=9, minute=0, timezone=TEHRAN),
                       id="daily_generate", max_instances=1, misfire_grace_time=3600)
    _scheduler.add_job(daily_insights, CronTrigger(hour=23, minute=45, timezone=TEHRAN),
                       id="daily_insights", max_instances=1, misfire_grace_time=3600)
    _scheduler.start()


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None

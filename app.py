# -*- coding: utf-8 -*-
"""سرور اصلی — پنل مدیریت اینستاگرام"""
import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core import db, scheduler
from core.analytics import fetch_and_store, recommendations, weekly_report_text
from core.content import caption_ideas, generate_caption
from core.ig_api import IGClient, IGError
from core.images import NewsRenderer, PostRenderer
from core.news import is_breaking, news_caption, seed_real_news
from core.setup import setup_payload

TEHRAN = ZoneInfo("Asia/Tehran")
BASE = Path(__file__).resolve().parent

app = FastAPI(title="پنل مدیریت اینستاگرام")

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/generated", StaticFiles(directory=db.GEN_DIR), name="generated")
app.mount("/uploads", StaticFiles(directory=db.UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def startup():
    db.init_db()
    db.seed_default_tasks()
    db.seed_news_sources()
    seed_samples()
    seed_real_news()
    scheduler.start()


@app.on_event("shutdown")
def shutdown():
    scheduler.stop()


# ---------------- ابزار ----------------
def shop_dict():
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


def parse_scheduled(value):
    """تبدیل ورودی زمان به ISO با منطقه تهران"""
    if not value:
        return None
    value = str(value).strip()
    try:
        if "+" in value or value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(TEHRAN).isoformat(timespec="seconds")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TEHRAN)
        return dt.astimezone(TEHRAN).isoformat(timespec="seconds")
    except ValueError:
        raise HTTPException(400, "فرمت زمان نامعتبر است")


def render_post_image(spec):
    kind = spec.get("kind", "post")
    tpl = spec.get("template", "product")
    product = None
    if spec.get("product_id"):
        product = db.get_product(spec["product_id"])
    else:
        product = {"name": spec.get("title", ""), "description": spec.get("text", ""),
                   "price": spec.get("price", ""), "image_path": "",
                   "emoji": spec.get("icon", "tag")}
    uid = datetime.now().strftime("%Y%m%d%H%M%S%f")
    path = str(db.GEN_DIR / f"{kind}_{uid}.jpg")
    shop = shop_dict()
    text = spec.get("text") or ((product or {}).get("description", "") if tpl in ("intro", "product") else "")
    PostRenderer(shop).render(
        kind=kind, template=tpl, product=product,
        title=spec.get("title") or (product or {}).get("name", ""),
        text=text,
        price=spec.get("price") or (product or {}).get("price", ""),
        old_price=spec.get("old_price", ""),
        extra=spec.get("extra", ""),
        icon=spec.get("icon") or ((product or {}).get("emoji") if (product or {}).get("emoji") else "tag"),
        out_path=path,
    )
    return path, product


def ensure_public_base(request: Request):
    try:
        base = str(request.base_url).rstrip("/")
    except Exception:
        return
    if "localhost" in base or "127.0.0.1" in base:
        return
    current = db.get_setting("public_base_url")
    if base != current:
        db.set_setting("public_base_url", base)


# ---------------- صفحات ----------------
@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/ping")
def ping():
    return {"ok": True}


# ---------------- وضعیت کلی ----------------
@app.get("/api/state")
def state(request: Request):
    ensure_public_base(request)
    s = db.all_settings()
    posts = db.get_posts()
    upcoming = [p for p in posts if p["status"] in ("scheduled", "ai_draft", "ready")][:8]
    return {
        "settings": s,
        "api_configured": bool(s.get("ig_access_token") and s.get("ig_user_id")),
        "counts": {
            "posts": len([p for p in posts if p["kind"] == "post"]),
            "stories": len([p for p in posts if p["kind"] == "story"]),
            "scheduled": len([p for p in posts if p["status"] == "scheduled"]),
            "ai_drafts": len([p for p in posts if p["status"] == "ai_draft"]),
            "ready": len([p for p in posts if p["status"] == "ready"]),
            "published": len([p for p in posts if p["status"] == "published"]),
            "products": len(db.get_products()),
        },
        "upcoming": upcoming,
        "activity": db.get_activity(12),
        "tasks": db.get_tasks(),
        "news_count": db.count_news(),
        "now": datetime.now(TEHRAN).isoformat(timespec="seconds"),
    }


@app.post("/api/settings")
def save_settings(payload: dict):
    allowed = {"shop_name", "shop_handle", "shop_tagline", "shop_phone", "phone",
               "cta", "color1", "color2", "accent", "post_time", "story_time",
               "story_time_2", "auto_generate_posts", "auto_publish_stories",
               "ig_access_token", "ig_user_id", "public_base_url",
               "page_type", "news_auto_fetch", "news_breaking_instant"}
    for k, v in payload.items():
        if k in allowed:
            db.set_setting(k, v)
    db.log_activity("⚙️ تنظیمات به‌روزرسانی شد.")
    return {"ok": True}


# ---------------- محصولات ----------------
@app.get("/api/products")
def products():
    return {"products": db.get_products()}


@app.post("/api/products")
def create_product(payload: dict):
    pid = db.add_product(payload.get("name", ""), payload.get("description", ""),
                         payload.get("price", ""), payload.get("emoji", "🛍️"),
                         payload.get("image_path", ""))
    db.log_activity(f"🛍️ محصول «{payload.get('name', '')}» اضافه شد.")
    return {"ok": True, "id": pid}


@app.post("/api/products/{pid}")
def update_product(pid: int, payload: dict):
    p = db.get_product(pid)
    if not p:
        raise HTTPException(404, "محصول پیدا نشد")
    with db.conn() as c:
        c.execute("UPDATE products SET name=?,description=?,price=?,emoji=?,image_path=? WHERE id=?",
                  (payload.get("name", p["name"]), payload.get("description", p["description"]),
                   payload.get("price", p["price"]), payload.get("emoji", p["emoji"]),
                   payload.get("image_path", p["image_path"]), pid))
    return {"ok": True}


@app.delete("/api/products/{pid}")
def remove_product(pid: int):
    db.delete_product(pid)
    return {"ok": True}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    dest = db.UPLOAD_DIR / name
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest), "url": f"/uploads/{name}"}


# ---------------- پست‌ها ----------------
@app.get("/api/posts")
def posts(status: str = "", kind: str = ""):
    st = status.split(",") if status else None
    return {"posts": db.get_posts(status=st, kind=kind or None)}


@app.post("/api/posts/generate")
def generate_post(payload: dict):
    kind = payload.get("kind", "post")
    tpl = payload.get("template", "product")
    product = None
    if payload.get("product_id"):
        product = db.get_product(payload["product_id"])
        if not product:
            raise HTTPException(404, "محصول پیدا نشد")

    image_path, product = render_post_image(payload)
    tpl_labels = {"offer": "پیشنهاد ویژه", "question": "سوال امروز",
                  "tip": "نکته روز", "quote": "جمله امروز"}
    pname = (product or {}).get("name", "")
    if payload.get("title"):
        title = payload["title"]
    elif tpl in ("intro", "product") and pname:
        title = pname
    elif tpl in tpl_labels:
        title = tpl_labels[tpl]
    else:
        title = "استوری جدید" if kind == "story" else "پست جدید"
    caption = (payload.get("caption") or "").strip()
    hashtags = (payload.get("hashtags") or "").strip()
    if not caption:
        caption, tags = generate_caption(
            kind, tpl, shop=shop_dict()["name"],
            product=pname or title,
            desc=(product or {}).get("description", "") or payload.get("text", ""),
            price=payload.get("price") or (product or {}).get("price", ""))
        hashtags = hashtags or tags
    scheduled_at = parse_scheduled(payload.get("scheduled_at"))
    status = "scheduled" if scheduled_at else "draft"
    pid = db.add_post(kind, title=title or "بدون عنوان", caption=caption, hashtags=hashtags,
                      image_path=image_path, template=tpl,
                      product_id=payload.get("product_id"),
                      scheduled_at=scheduled_at, status=status)
    db.log_activity(f"🎨 {'استوری' if kind == 'story' else 'پست'} «{title}» ساخته شد.")
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}")
def edit_post(pid: int, payload: dict):
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    fields = {}
    for k in ("title", "caption", "hashtags", "template"):
        if k in payload:
            fields[k] = payload[k]
    if "scheduled_at" in payload:
        fields["scheduled_at"] = parse_scheduled(payload["scheduled_at"])
        if fields["scheduled_at"] and p["status"] in ("draft", "ai_draft", "ready"):
            fields["status"] = "scheduled"
        if not fields["scheduled_at"] and p["status"] == "scheduled":
            fields["status"] = "draft"
    if "kind" in payload:
        fields["kind"] = payload["kind"]
    db.update_post(pid, **fields)
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}/regenerate")
def regenerate(pid: int, payload: dict):
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    spec = {
        "kind": p["kind"], "template": p["template"], "product_id": p["product_id"],
        "title": p["title"], "text": payload.get("text", ""),
        "price": payload.get("price", ""), "old_price": payload.get("old_price", ""),
        "extra": payload.get("extra", ""),
    }
    path, _ = render_post_image(spec)
    db.update_post(pid, image_path=path)
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}/schedule")
def schedule_post(pid: int, payload: dict):
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    at = parse_scheduled(payload.get("scheduled_at"))
    db.update_post(pid, scheduled_at=at, status="scheduled" if at else p["status"], error="")
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}/approve")
def approve_post(pid: int, payload: dict):
    """تأیید پیش‌نویس هوشمند → زمان‌بندی"""
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    at = parse_scheduled(payload.get("scheduled_at")) or p["scheduled_at"]
    db.update_post(pid, status="scheduled" if at else "draft", scheduled_at=at)
    db.log_activity(f"👍 پیش‌نویس «{p['title']}» تأیید و زمان‌بندی شد.")
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}/publish")
def publish_now(pid: int):
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    if p["status"] != "scheduled":
        db.update_post(pid, status="scheduled",
                       scheduled_at=datetime.now(TEHRAN).isoformat(timespec="seconds"))
    ok = scheduler.publish_post(pid)
    if not ok:
        post = db.get_post(pid)
        raise HTTPException(400, post.get("error") or "انتشار ناموفق بود")
    return {"ok": True, "post": db.get_post(pid)}


@app.post("/api/posts/{pid}/mark_published")
def mark_published(pid: int):
    """علامت‌گذاری دستی: کاربر خودش منتشر کرده"""
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    db.update_post(pid, status="published", published_at=datetime.now(TEHRAN).isoformat(timespec="seconds"))
    db.log_activity(f"✅ «{p['title']}» به‌صورت دستی منتشر شد (ثبت شد).")
    return {"ok": True}


@app.delete("/api/posts/{pid}")
def remove_post(pid: int):
    db.delete_post(pid)
    return {"ok": True}


@app.get("/api/posts/{pid}/package")
def post_package(pid: int):
    p = db.get_post(pid)
    if not p:
        raise HTTPException(404, "پست پیدا نشد")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        img = Path(p["image_path"])
        if img.exists():
            z.write(img, img.name)
        cap = (p["caption"] or "") + "\n\n" + (p["hashtags"] or "")
        z.writestr("کپشن.txt", cap.strip().encode("utf-8"))
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename=post_{pid}.zip"})


# ---------------- اخبار ----------------
def _news_view(item):
    from core.news import extract_quotes, extract_numbers
    item = dict(item)
    full = (item.get("summary") or "") + " " + (item.get("headline") or "")
    item["stats"] = extract_numbers(full)
    item["quotes"] = extract_quotes(full)
    return item


@app.get("/api/news")
def news_list(limit: int = 40, unused_only: int = 0):
    return {"news": [_news_view(n) for n in db.get_news(limit=limit, unused_only=bool(unused_only))],
            "count": db.count_news()}


@app.post("/api/news/fetch")
def news_fetch():
    from core.news import fetch_all
    try:
        stats = fetch_all()
    except Exception as e:
        raise HTTPException(400, f"دریافت اخبار ناموفق بود: {e}")
    if not stats["fetched"] and stats["errors"]:
        failed = "، ".join(stats["errors"][:4])
        raise HTTPException(400, (
            f"از این سرور امکان اتصال به منابع خبری ({failed}) وجود ندارد "
            "(اینترنت این محیط محدود است). خبرهایی که قبلاً دریافت شده‌اند موجودند؛ "
            "می‌توانی خبر دستی اضافه کنی. روی سرور خودت این محدودیت نیست."))
    if stats["new"]:
        db.log_activity(f"📰 {stats['new']} خبر جدید از منابع دریافت شد.")
    made_instant = scheduler.instant_breaking_stories()
    return {"ok": True, "instant_stories": made_instant, **stats}


@app.post("/api/news/manual")
def news_manual(payload: dict):
    headline = (payload.get("headline") or "").strip()
    if not headline:
        raise HTTPException(400, "تیتر خبر را وارد کن")
    from core.news import categorize
    nid = db.add_news(
        headline,
        summary=(payload.get("summary") or "").strip(),
        link=(payload.get("link") or "").strip(),
        source=(payload.get("source") or "دستی").strip(),
        category=payload.get("category") or categorize(headline),
        published_at=datetime.now(TEHRAN).strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.log_activity(f"📰 خبر دستی اضافه شد: {headline[:50]}")
    made_instant = scheduler.instant_breaking_stories()
    return {"ok": True, "id": nid, "instant_stories": made_instant}


@app.delete("/api/news/{nid}")
def news_delete(nid: int):
    db.delete_news(nid)
    return {"ok": True}


@app.post("/api/news/{nid}/post")
def news_to_post(nid: int, payload: dict):
    item = db.get_news_item(nid)
    if not item:
        raise HTTPException(404, "خبر پیدا نشد")
    from core.news import template_data
    tpl, stats, quotes = template_data(item, payload.get("template", "auto"))
    shop = shop_dict()
    uid = datetime.now().strftime("%Y%m%d%H%M%S")
    path = str(db.GEN_DIR / f"post_news{uid}.jpg")
    NewsRenderer(shop).render(
        kind="post", headline=item["headline"], summary=item["summary"],
        source=item["source"], category=item["category"],
        breaking=is_breaking(item["headline"] + " " + item["summary"]),
        out_path=path, template=tpl, stats=stats, quotes=quotes,
    )
    caption, tags = news_caption(item, shop["name"])
    scheduled_at = parse_scheduled(payload.get("scheduled_at"))
    pid = db.add_post(
        "post", title=item["headline"][:90], caption=caption, hashtags=tags,
        image_path=path, template="news",
        scheduled_at=scheduled_at,
        status="scheduled" if scheduled_at else "ai_draft",
    )
    db.mark_news_used(nid)
    db.log_activity(f"🗞️ پست خبری (قالب {tpl}) از خبر «{item['headline'][:40]}…» ساخته شد.")
    return {"ok": True, "post": db.get_post(pid), "template_used": tpl}


@app.post("/api/news/{nid}/story")
def news_to_story(nid: int, payload: dict):
    item = db.get_news_item(nid)
    if not item:
        raise HTTPException(404, "خبر پیدا نشد")
    from core.news import template_data
    tpl, stats, quotes = template_data(item, payload.get("template", "auto"))
    shop = shop_dict()
    uid = datetime.now().strftime("%Y%m%d%H%M%S")
    path = str(db.GEN_DIR / f"story_news{uid}.jpg")
    NewsRenderer(shop).render(
        kind="story", headline=item["headline"], summary=item["summary"],
        source=item["source"], category=item["category"],
        breaking=is_breaking(item["headline"] + " " + item["summary"]),
        out_path=path, template=tpl, stats=stats, quotes=quotes,
    )
    caption, tags = news_caption(item, shop["name"], include_link=True)
    scheduled_at = parse_scheduled(payload.get("scheduled_at"))
    pid = db.add_post(
        "story", title=item["headline"][:90], caption=caption, hashtags=tags,
        image_path=path, template="news",
        scheduled_at=scheduled_at,
        status="scheduled" if scheduled_at else "draft",
    )
    db.mark_news_used(nid)
    db.log_activity(f"📱 استوری خبری (قالب {tpl}) از خبر «{item['headline'][:40]}…» ساخته شد.")
    return {"ok": True, "post": db.get_post(pid), "template_used": tpl}


@app.post("/api/news/generate")
def news_generate_today():
    made = scheduler.generate_news_content(fetch_first=True)
    return {"ok": True, "made": made}


@app.get("/api/news/sources")
def news_sources():
    return {"sources": db.get_news_sources()}


@app.post("/api/news/sources")
def news_add_source(payload: dict):
    name = (payload.get("name") or "").strip()
    url = (payload.get("url") or "").strip()
    if not name or not url:
        raise HTTPException(400, "نام و آدرس فید را وارد کن")
    sid = db.add_news_source(name, url, payload.get("category") or "عمومی",
                             enabled=1, is_default=0)
    return {"ok": True, "id": sid}


@app.post("/api/news/sources/{sid}")
def news_update_source(sid: int, payload: dict):
    fields = {}
    for k in ("name", "url", "category", "enabled"):
        if k in payload:
            fields[k] = payload[k]
    db.update_news_source(sid, **fields)
    return {"ok": True}


@app.delete("/api/news/sources/{sid}")
def news_delete_source(sid: int):
    db.delete_news_source(sid)
    return {"ok": True}


# ---------------- راه‌اندازی پیج ----------------
@app.get("/api/setup")
def setup_info():
    return setup_payload()


# ---------------- اتصال اینستاگرام ----------------
@app.post("/api/ig/test")
def ig_test(payload: dict):
    token = payload.get("access_token", "").strip()
    ig_id = payload.get("ig_user_id", "").strip()
    if not (token and ig_id):
        raise HTTPException(400, "توکن و شناسه اکانت را وارد کن")
    ig = IGClient(token, ig_id)
    try:
        info = ig.test()
    except IGError as e:
        raise HTTPException(400, str(e))
    db.set_setting("ig_access_token", token)
    db.set_setting("ig_user_id", ig_id)
    db.log_activity("🔌 اتصال به اینستاگرام برقرار شد: @" + info.get("username", ""))
    return {"ok": True, "info": info}


@app.post("/api/ig/discover")
def ig_discover(payload: dict):
    token = payload.get("access_token", "").strip()
    if not token:
        raise HTTPException(400, "توکن را وارد کن")
    try:
        accounts = IGClient.discover(token)
    except IGError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "accounts": accounts}


@app.post("/api/ig/check_public")
def check_public():
    import requests as rq
    base = db.get_setting("public_base_url")
    if not base:
        return {"ok": False, "message": "آدرس عمومی سرور ثبت نشده است."}
    try:
        r = rq.get(base + "/api/ping", timeout=10)
        return {"ok": r.status_code == 200,
                "message": "سرور از اینترنت قابل دسترسی است؛ انتشار خودکار ممکن است." if r.status_code == 200
                else f"پاسخ غیرمنتظره: {r.status_code}"}
    except rq.RequestException as e:
        return {"ok": False,
                "message": "سرور از اینترنت قابل دسترسی نیست. برای انتشار خودکار، اپ را روی یک سرور عمومی "
                           "(مثلاً Railway یا یک VPS کوچک) اجرا کن؛ در غیر این صورت از انتشار دستی استفاده کن."}


# ---------------- آنالیز ----------------
@app.get("/api/analytics")
def analytics():
    metrics = db.get_metrics(60)
    use_api = bool(db.get_setting("ig_access_token") and db.get_setting("ig_user_id"))
    return {"metrics": metrics, "use_api": use_api}


@app.post("/api/analytics/fetch")
def analytics_fetch():
    token = db.get_setting("ig_access_token")
    ig_id = db.get_setting("ig_user_id")
    if not (token and ig_id):
        raise HTTPException(400, "اول اتصال اینستاگرام را در تنظیمات برقرار کن")
    try:
        summary = fetch_and_store(token, ig_id)
    except IGError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "summary": summary}


@app.post("/api/analytics/manual")
def analytics_manual(payload: dict):
    today = datetime.now(TEHRAN).strftime("%Y-%m-%d")
    db.upsert_metric(
        today,
        followers=int(payload.get("followers") or 0),
        following=int(payload.get("following") or 0) or None,
        media_count=int(payload.get("media_count") or 0) or None,
        reach=int(payload.get("reach") or 0) or None,
        impressions=int(payload.get("impressions") or 0) or None,
        profile_views=int(payload.get("profile_views") or 0) or None,
        source="manual",
    )
    db.log_activity("📝 آمار امروز به‌صورت دستی ثبت شد.")
    return {"ok": True}


@app.post("/api/analytics/reset")
def analytics_reset():
    with db.conn() as c:
        c.execute("DELETE FROM metrics")
    db.log_activity("🗑️ داده‌های آماری پاک شد.")
    return {"ok": True}


@app.get("/api/recommendations")
def get_recommendations():
    s = db.all_settings()
    use_api = bool(s.get("ig_access_token") and s.get("ig_user_id"))
    return {"recommendations": recommendations(use_api, s.get("ig_access_token"), s.get("ig_user_id"))}


@app.get("/api/report")
def get_report():
    return {"report": weekly_report_text()}


# ---------------- تسک‌های رشد ----------------
@app.post("/api/tasks")
def create_task(payload: dict):
    tid = db.add_task(payload.get("text", ""))
    return {"ok": True, "id": tid}


@app.post("/api/tasks/{tid}/toggle")
def toggle_task_endpoint(tid: int):
    t = db.get_tasks()
    target = next((x for x in t if x["id"] == tid), None)
    if target:
        db.toggle_task(tid, not target["done"])
    return {"ok": True}


@app.delete("/api/tasks/{tid}")
def remove_task(tid: int):
    db.delete_task(tid)
    return {"ok": True}


# ---------------- محتوای هوشمند ----------------
@app.post("/api/content/ideas")
def content_ideas(payload: dict):
    product = db.get_product(payload.get("product_id")) if payload.get("product_id") else None
    ideas = caption_ideas(
        product=(product or {}).get("name", "") or payload.get("title", ""),
        desc=(product or {}).get("description", "") or payload.get("text", ""),
        price=(product or {}).get("price", "") or payload.get("price", ""),
        shop=shop_dict()["name"],
    )
    return {"ideas": ideas}


@app.post("/api/content/auto")
def auto_generate_now():
    scheduler.daily_generate()
    db.log_activity("🤖 تولید محتوای امروز به‌صورت دستی اجرا شد.")
    return {"ok": True}


# ---------------- داده نمونه اولیه ----------------
def seed_samples():
    if db.get_setting("seeded") == "1":
        return
    db.set_setting("seeded", "1")
    samples = sorted((BASE / "assets" / "samples").glob("*.*")) if (BASE / "assets" / "samples").exists() else []
    now = datetime.now(TEHRAN)

    if not db.get_products():
        sample_products = [
            ("شمع دست‌ساز معطر", "با موم طبیعی و رایحه آرامش‌بخش؛ انتخابی خاص برای خانه شما", "185000", "🕯️"),
            ("لیوان سرامیکی دست‌ساز", "لعاب مات، مقاوم به حرارت و مناسب ماشین ظرفشویی", "240000", "☕"),
            ("کیف چرم طبیعی", "چرم گاوی درجه یک، دوخت دست، طرح مینیمال", "980000", "👜"),
        ]
        for i, (name, desc, price, emoji) in enumerate(sample_products):
            img = samples[i] if i < len(samples) else ""
            db.add_product(name, desc, price, emoji, str(img) if img else "")
        db.log_activity("🛍️ ۳ محصول نمونه اضافه شد — می‌توانی در تب محصولات عوضشان کنی.")

    # دو پست و یک استوری نمونه در آینده
    if not db.get_posts():
        products = db.get_products()
        p1 = products[0] if products else None
        tomorrow = (now + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
        story_time = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        from core.content import generate_caption as _gc
        if p1:
            cap, tags = _gc("post", "intro", shop="فروشگاه من", product=p1["name"],
                            desc=p1["description"], price=p1["price"])
            path = str(db.GEN_DIR / f"post_demo1.jpg")
            PostRenderer(shop_dict()).render(kind="post", template="intro", product=p1,
                                             title=p1["name"], text=p1["description"],
                                             price=p1["price"], out_path=path)
            db.add_post("post", title=p1["name"], caption=cap, hashtags=" ".join(tags),
                        image_path=path, template="intro", product_id=p1["id"],
                        scheduled_at=tomorrow.isoformat(timespec="seconds"), status="scheduled")
        p2 = products[1] if len(products) > 1 else None
        if p2:
            cap, tags = _gc("story", shop="فروشگاه من", product=p2["name"], desc=p2["description"], price=p2["price"])
            path = str(db.GEN_DIR / f"story_demo1.jpg")
            PostRenderer(shop_dict()).render(kind="story", template="product", product=p2,
                                             title=p2["name"], text=p2["description"],
                                             price=p2["price"], out_path=path)
            db.add_post("story", title=p2["name"], caption=cap, hashtags=" ".join(tags),
                        image_path=path, template="product", product_id=p2["id"],
                        scheduled_at=story_time.isoformat(timespec="seconds"), status="scheduled")
        db.log_activity("🎉 محتوای نمونه ساخته شد: ۱ پست + ۱ استوری زمان‌بندی‌شده.")

    # سری داده نمونه برای نمودار (تا وقتی آمار واقعی ثبت نشود)
    if not db.get_metrics(60):
        base_f = 842
        for i in range(14, -1, -1):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            followers = base_f + (14 - i) * 23 + (i % 3) * 7
            reach = followers * 3 + (i % 5) * 40
            db.upsert_metric(day, followers=followers, following=312, media_count=28 + (14 - i),
                             reach=reach, impressions=int(reach * 1.4),
                             profile_views=int(reach * 0.35), source="demo")
        db.log_activity("📈 داده‌ی نمونه برای نمودار آنالیز بارگذاری شد (از تب آنالیز می‌توانی پاکش کنی).")

# -*- coding: utf-8 -*-
"""راه‌اندازی پیج از صفر: اسم/یوزرنیم پیشنهادی، بیو، عکس پروفایل و کاور هایلایت"""
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from . import db
from .images import (draw_center, draw_decor, draw_icon, draw_pill, font,
                     gradient_bg, hex_rgb, shaped)

BASE_DIR = Path(__file__).resolve().parent.parent
BRAND_ASSETS = BASE_DIR / "assets" / "brand"
BRAND_OUT = db.GEN_DIR / "brand"

HIGHLIGHTS = [
    ("فوری", "#DC2626", "#7F1D1D", "bulb"),
    ("ایران", "#047857", "#064E3B", "heart"),
    ("جهان", "#1D4ED8", "#312E81", "chat"),
    ("اقتصاد", "#B45309", "#78350F", "percent"),
    ("ورزش", "#7C3AED", "#4F46E5", "star"),
    ("فرهنگ", "#BE185D", "#701A75", "gift"),
]

NEWS_NAMES = [
    "اخبار روز | ایران و جهان",
    "خبرفوری ۲۴",
    "آخرین خبر | ایران و جهان",
    "تیتر اول",
    "رویداد ۲۴",
    "جهان امروز",
    "اخبار لحظه‌ای ایران و جهان",
    "نبض خبر",
    "پالس خبر",
    "ساعت خبر",
    "روایت امروز",
    "رسانه امروز",
    "تحریریه خبر",
    "خبربان",
    "لحظه‌ها",
    "خبرگردی",
    "کاغذ خبر",
    "فانوس خبر",
    "شب خبر",
    "خلاصه خبر",
    "ایران و جهان نیوز",
    "خبر اکسپرس",
]

NEWS_USERNAMES = [
    "akhbar24", "khabar.fouri", "akhbar.roz", "iran.world.news",
    "news.fa24", "akhbar.fouri24", "titr.aval",
]

AI_NAMES = [
    "هوشینو",
    "هوش مصنوعی به زبان ساده",
    "ای‌آی فارسی",
    "ذهن دیجیتال",
    "دنیای هوش مصنوعی",
    "AI روز",
    "مغز مصنوعی",
    "هوش نو",
    "ربات‌ها و ما",
    "ژرفای هوش",
]

AI_USERNAMES = [
    "hooshino", "ai.farsi", "zehn.digital", "donya.ai", "ai.rooz",
    "maghz.masnoei", "hoosh.no", "robot.ha", "zharf.ai",
]

AI_HIGHLIGHTS = [
    ("ابزارها", "#6D28D9", "#312E81", "gift"),
    ("پرامپت", "#1D4ED8", "#312E81", "chat"),
    ("نکته‌ها", "#047857", "#064E3B", "bulb"),
    ("اخبار AI", "#B91C1C", "#450A0A", "star"),
    ("مقایسه", "#B45309", "#78350F", "percent"),
    ("آینده", "#BE185D", "#701A75", "heart"),
]

SETUP_STEPS = {
    "ai": [
        ("📱 ساخت اکانت اینستاگرام",
         "در اپلیکیشن اینستاگرام با شماره تلفن یا ایمیل ثبت‌نام کن و یوزرنیم پیشنهادی را انتخاب کن."),
        ("🎨 تکمیل پروفایل",
         "عکس پروفایل و بیوی آماده را از همین صفحه دانلود کن و در پروفایل بگذار."),
        ("💼 تبدیل به حساب حرفه‌ای",
         "تنظیمات ← نوع حساب ← حرفه‌ای ← دسته «علم و فناوری / آموزش». "
         "این کار برای آنالیز و انتشار خودکار لازم است."),
        ("🔗 اتصال به فیسبوک‌پیج (برای انتشار خودکار)",
         "در تب «تنظیمات ← اتصال اینستاگرام» راهنمای API متا را دنبال کن."),
        ("🤖 انتشار اولین محتواها",
         "از تب «تقویم انتشار»، پست‌های «دانستنی» و «معرفی ابزار» را با «⬇️ بسته» دانلود و منتشر کن. "
         "۳ پست اول، هویت پیج را می‌سازند."),
        ("📈 ادامه خودکار",
         "تولید خودکار روزانه و «استوری خبر AI» را روشن نگه دار؛ بعد از ۲ هفته تب آنالیز روند رشد را نشان می‌دهد."),
    ],
    "news": [
        ("📱 ساخت اکانت اینستاگرام",
         "در اپلیکیشن اینستاگرام (اندروید/iOS) با شماره تلفن یا ایمیل ثبت‌نام کن. "
         "یوزرنیم را از پیشنهادهای بالا انتخاب کن (بعداً هم قابل تغییر است)."),
        ("🎨 تکمیل پروفایل",
         "عکس پروفایل و بیوی آماده را از همین صفحه دانلود و در پروفایل بگذار؛ "
         "نام پیج را فارسی بگذار چون جستجوی کاربران ایرانی با فارسی بهتر است."),
        ("💼 تبدیل به حساب حرفه‌ای",
         "تنظیمات ← نوع حساب و ابزارها ← تغییر به حساب حرفه‌ای ← دسته «اخبار/رسانه»."
         "این کار برای آنالیز و انتشار خودکار لازم است."),
        ("🔗 اتصال به فیسبوک‌پیج (برای انتشار خودکار)",
         "در تب «تنظیمات ← اتصال اینستاگرام» راهنمای قدم‌به‌قدم API متا را دنبال کن."),
        ("🚀 انتشار اولین محتواها",
         "از تب «تقویم انتشار»، پست‌ها و استوری‌های آماده را با دکمه «⬇️ بسته» دانلود "
         "و در اپ اینستاگرام منتشر کن. ۳ پست اول، هویت پیج را می‌سازند."),
        ("📈 ادامه خودکار",
         "مطمئن شو «تولید خودکار روزانه» و «استوری فوری» روشن است؛ "
         "بعد از ۲ هفته، تب آنالیز روند رشد را نشان می‌دهد."),
    ],
    "shop": [
        ("📱 ساخت اکانت اینستاگرام",
         "در اپلیکیشن اینستاگرام با شماره تلفن یا ایمیل ثبت‌نام کن و یوزرنیم پیشنهادی را انتخاب کن."),
        ("🎨 تکمیل پروفایل",
         "عکس پروفایل (لوگوی فروشگاه) و بیوی آماده را از همین صفحه دانلود کن و بگذار."),
        ("💼 تبدیل به حساب حرفه‌ای",
         "تنظیمات ← نوع حساب ← حرفه‌ای ← دسته «خرید و فروش / فروشگاه». "
         "حساب بیزینس، دکمه تماس و آمار در اختیارت می‌گذارد."),
        ("🔗 اتصال به فیسبوک‌پیج (برای انتشار خودکار)",
         "در تب «تنظیمات ← اتصال اینستاگرام» راهنمای API متا را دنبال کن."),
        ("🛍️ معرفی محصولات",
         "اولین پست‌ها را از تب «تقویم انتشار» منتشر کن؛ بعد محصولاتت را در تب «محصولات» اضافه کن."),
        ("📈 ادامه خودکار",
         "تولید خودکار روزانه را روشن نگه دار و هفته‌ای یک‌بار تب آنالیز را چک کن."),
    ],
}


def _shop():
    s = db.all_settings()
    return {
        "name": s.get("shop_name", "فروشگاه من"),
        "handle": s.get("shop_handle", ""),
        "tagline": s.get("shop_tagline", ""),
        "phone": s.get("shop_phone", s.get("phone", "")),
        "cta": s.get("cta", "برای سفارش دایرکت بده"),
        "color1": s.get("color1", "#7C3AED"),
        "color2": s.get("color2", "#4F46E5"),
        "accent": s.get("accent", "#FBBF24"),
        "page_type": s.get("page_type", "shop"),
    }


def name_ideas():
    shop = _shop()
    if shop["page_type"] == "news":
        ideas = NEWS_NAMES[:]
        if shop["name"] and shop["name"] != "فروشگاه من":
            ideas.insert(0, shop["name"])
    elif shop["page_type"] == "ai":
        ideas = AI_NAMES[:]
        if shop["name"] and shop["name"] != "فروشگاه من":
            ideas.insert(0, shop["name"])
    else:
        ideas = [shop["name"] or "فروشگاه من"]
        if shop["tagline"]:
            ideas.append(f"{shop['name']} | {shop['tagline']}")
        ideas += [f"{shop['name']} | فروشگاه آنلاین", f"{shop['name']} | ارسال سریع"]
    return list(dict.fromkeys(ideas))[:10]


def username_ideas():
    shop = _shop()
    handle = re.sub(r"[^a-z0-9_.]", "", (shop["handle"] or "").lower())
    stem = handle.split(".")[0] if handle else ""
    if shop["page_type"] == "news":
        pool = NEWS_USERNAMES[:]
        if stem:
            variants = [handle]
            if not stem.endswith(("news", "24")):
                variants.append(f"{stem}24")
            variants.append(f"{stem}_ir")
            if not handle.endswith(".news"):
                variants.append(f"{stem}.news")
            pool = variants + pool
    elif shop["page_type"] == "ai":
        pool = AI_USERNAMES[:]
        if stem:
            variants = [handle]
            if stem != "ai" and not stem.startswith("ai."):
                variants.append(f"ai.{stem}")
            pool = variants + pool
    else:
        pool = [f"{stem}.shop", f"{stem}.ir", f"{stem}_store", f"shop.{stem}"] if stem else []
        if handle:
            pool.insert(0, handle)
        if not pool:
            pool = ["my.shop.ir", "my_shop24", "shop.man.ir"]
    return list(dict.fromkeys(pool))[:6]


def build_bio():
    shop = _shop()
    if shop["page_type"] == "news":
        lines = [
            "📰 " + (shop["name"] or "اخبار روز"),
            "🔴 اخبار فوری و مهم ایران و جهان",
        ]
        if shop["tagline"]:
            lines.append(shop["tagline"])
        else:
            lines.append("⏱ پوشش لحظه‌ای رویدادها")
        if shop["phone"]:
            lines.append("📩 ارتباط/تبادل: " + shop["phone"])
        lines.append("برای خبررسانی سریع، دنبالمان کنید ⬇️")
        return "\n".join(lines)
    if shop["page_type"] == "ai":
        lines = [
            "🤖 " + (shop["name"] or "هوشینو"),
            "هوش مصنوعی به زبان ساده",
            "🧠 دانستنی، ابزار و پرامپت روز",
            "📰 تازه‌ترین خبرهای هوش مصنوعی دنیا",
        ]
        if shop["tagline"] and shop["tagline"] not in lines:
            lines.append(shop["tagline"])
        lines.append("هر روز یک قدم هوشمندتر ⬇️")
        return "\n".join(lines)
    lines = ["🛍️ " + (shop["name"] or "فروشگاه من")]
    if shop["tagline"]:
        lines.append(shop["tagline"])
    lines.append(shop["cta"] or "برای سفارش دایرکت بده")
    if shop["phone"]:
        lines.append("📞 " + shop["phone"])
    return "\n".join(lines)


# ---------- تولید دارایی‌های برند ----------
def _make_profile_text(shop):
    S = 512
    c1, c2 = hex_rgb(shop["color1"]), hex_rgb(shop["color2"])
    img = gradient_bg((S, S), c1, c2)
    img = draw_decor(img, c1, c2, seed=11)
    d = ImageDraw.Draw(img)
    # حلقه تاکید
    d.ellipse([96, 96, S - 96, S - 96], outline=hex_rgb(shop["accent"]), width=10)
    # حرف اول نام
    name = (shop["name"] or "پ").strip()
    letter = name[0]
    lf = font("black", 220)
    bbox = draw_center(d, S / 2, S / 2 - 40, letter, lf, (255, 255, 255))
    # هندل
    handle = shop["handle"] or ""
    if handle:
        hf = font("semibold", 30)
        draw_pill(d, S / 2, S - 150, "@" + handle, hf, (255, 255, 255), (0, 0, 0, 60),
                  pad_x=26, pad_y=10)
    out = BRAND_OUT / "profile_text.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=93)
    return out


def _make_highlight(label, color1, color2, icon):
    S = 512
    c1, c2 = hex_rgb(color1), hex_rgb(color2)
    img = gradient_bg((S, S), c1, c2)
    img = draw_decor(img, c1, c2, seed=hash(label) % 9999)
    d = ImageDraw.Draw(img)
    draw_icon(d, icon, S / 2, S / 2 - 70, 150, (255, 255, 255))
    lf = font("bold", 62)
    draw_center(d, S / 2, S - 190, label, lf, (255, 255, 255))
    out = BRAND_OUT / f"hl_{label}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


def ensure_brand_assets():
    """ساخت/به‌روزرسانی عکس پروفایل و کاور هایلایت‌ها در generated/brand"""
    BRAND_OUT.mkdir(parents=True, exist_ok=True)
    shop = _shop()

    # لوگوی AI (در صورت وجود در assets)
    ai_src = BRAND_ASSETS / "profile_ai.jpg"
    ai_dst = BRAND_OUT / "profile_ai.jpg"
    if ai_src.exists() and not ai_dst.exists():
        shutil.copy(ai_src, ai_dst)

    # لوگوی متنی (همیشه تازه بر اساس نام پیج)
    _make_profile_text(shop)

    # کاور هایلایت
    made = []
    highlights = AI_HIGHLIGHTS if shop["page_type"] == "ai" else HIGHLIGHTS
    for label, c1, c2, icon in highlights:
        _make_highlight(label, c1, c2, icon)
        made.append({"label": label, "url": f"/generated/brand/hl_{label}.jpg"})
    return made


def setup_payload():
    ensure_brand_assets()
    shop = _shop()
    return {
        "page_type": shop["page_type"],
        "names": name_ideas(),
        "usernames": username_ideas(),
        "bio": build_bio(),
        "steps": SETUP_STEPS.get(shop["page_type"], SETUP_STEPS["shop"]),
        "assets": {
            "profile_text": "/generated/brand/profile_text.jpg",
            "profile_ai": "/generated/brand/profile_ai.jpg",
            "highlights": ensure_brand_assets(),
        },
    }

# -*- coding: utf-8 -*-
"""تولید کپشن و هشتگ فارسی برای پست و استوری"""
import random

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(value):
    return str(value).translate(FA_DIGITS)


def fa_price(price):
    """'298000' -> '۲۹۸٬۰۰۰ تومان'"""
    if not price:
        return ""
    try:
        digits = fa_num(int(str(price).replace(",", "").replace("٬", "")))
        parts, out = [], ""
        for i, ch in enumerate(reversed(digits)):
            out = ch + out
            if (i + 1) % 3 == 0 and i + 1 < len(digits):
                out = "٬" + out
        return out + " تومان"
    except (ValueError, TypeError):
        return str(price) + " تومان"


CAPTION_TEMPLATES = {
    "intro": [
        "✨ جدید رسید: {product}!\n{desc}\n\n{price_line}\nسفارش فقط با یک پیام دایرکت 💬\n{cta}\n\n{hashtags}",
        "معرفی می‌کنیم: {product} 🌟\n{desc}\n{price_line}\n\nکیفیت تضمینی، ارسال سریع به سراسر کشور 🚚\n{cta}\n\n{hashtags}",
        "{product} اینجاست! 😍\n{desc}\n{price_line}\n\nتعداد محدود — همین امروز سفارش بده\n{cta}\n\n{hashtags}",
    ],
    "offer": [
        "🎉 پیشنهاد ویژه این هفته: {product}\n{desc}\n\n{price_line}\nفقط تا پایان هفته فرصت داری!\n{cta}\n\n{hashtags}",
        "🔥 تخفیف ویژه روی {product}\n{price_line}\n{desc}\n\nعجله کن، موجودی محدوده!\n{cta}\n\n{hashtags}",
        "فرصت استثنایی! 😍\n{product} با قیمت ویژه‌ی این هفته\n{price_line}\n{desc}\n\n{cta}\n\n{hashtags}",
    ],
    "question": [
        "یه سوال از شما 😊\n{product}\n{desc}\n\nشما کدوم رنگ/مدلش رو بیشتر دوست دارید؟ کامنت کنید! 👇\n{cta}\n\n{hashtags}",
        "نظر شما چیه؟ 💭\n{product} — {desc}\n{price_line}\n\nاگر جای ما بودید، این محصول رو چطور معرفی می‌کردید؟\nکامنت‌ها رو می‌خونیم! 👇\n\n{hashtags}",
        "چالش کوچیک! 🧐\n{product} رو ببینید...\n{desc}\n\nحدس بزنید از چه متریالی ساخته شده؟ درست حدس بزنی، تخفیف داری! 🎁\n\n{hashtags}",
    ],
    "testimonial": [
        "یکی از مشتری‌هامون نوشته: 💬\n«{desc}»\n\nاین نظر درباره‌ی {product} هست.\n{price_line}\n\nتجربه‌ی شما چطور بوده؟ کامنت کنید 👇\n\n{hashtags}",
        "اعتماد شما بزرگ‌ترین سرمایه‌ی ماست 🤍\n{product}\n{desc}\n{price_line}\n\n+۱۰۰۰ سفارش موفق و رضایت کامل مشتری‌ها\n{cta}\n\n{hashtags}",
    ],
    "tip": [
        "💡 نکته روز:\n{desc}\n\nاین نکته رو برای {product} هم می‌تونی استفاده کنی 😉\n\n{hashtags}",
        "می‌دونستید؟ 🤔\n{desc}\n\nهمین حالا {product} رو با کیفیت تضمینی سفارش بده 👇\n{cta}\n\n{hashtags}",
    ],
}

STORY_CAPTION_TEMPLATES = [
    "{product} رو دیدی؟ 😍\n{desc}\n{price_line}\n\nبرای سفارش به دایرکت پیام بده 💬",
    "پشت‌صحنه‌ی آماده‌سازی {product} 🎬\n{desc}\n\nهمین امروز سفارش بده! 🚚",
    "فقط امروز! ⏰\n{product}\n{price_line}\n\nدایرکت بدید تا راهنماییتون کنیم 😊",
    "سوال پرتکرار امروز: {desc}\nجواب رو کامل توی هایلایت «سوالات» گذاشتیم 😉",
    "مشتری عزیز، ممنون از اعتمادت 🤍\n{product} امروز ارسال شد!\n\nشما هم سفارش بدید 👇",
]

QUOTES = [
    "کیفیت یعنی انجام درستِ کار، وقتی کسی نگاه نمی‌کند.",
    "مشتری مهم‌ترین بازدیدکننده‌ی کسب‌وکار ماست.",
    "موفقیت، مجموع تلاش‌های کوچکی است که هر روز تکرار می‌شوند.",
    "اعتماد مثل یک شیشه است؛ وقتی شکست، ترمیمش سخت است.",
    "هر محصولی که می‌فرستیم، امضای ما روی آن است.",
    "بهترین تبلیغ، مشتری راضی است.",
]

TIPS = [
    "برای نگهداری محصول، آن را دور از نور مستقیم خورشید قرار دهید.",
    "ارسال همه‌ی سفارش‌ها حداکثر تا ۲۴ ساعت بعد از ثبت انجام می‌شود.",
    "بسته‌بندی سفارش‌ها با محافظ مخصوص انجام می‌شود تا سالم به دستتان برسد.",
    "برای سفارش عمده، دایرکت بدید تا قیمت ویژه بگیرید.",
    "هر سفارش شامل یک هدیه‌ی کوچک از طرف ماست 🎁",
    "پرداخت در محل برای تهران فعال است.",
]

QUESTIONS = [
    "کدوم محصول پیج رو بیشتر دوست دارید؟ 👇",
    "ترجیح می‌دید استوری‌ها چه ساعتی منتشر بشن؟",
    "چه محصول جدیدی دوست دارید به فروشگاه اضافه کنیم؟",
    "به نظرتون بهترین خریدتون از ما چی بوده؟",
    "این پست رو برای دوستتون بفرستید اگر فکر می‌کنید بهش نیاز داره! 💌",
]

HASHTAG_BASE = [
    "فروشگاه_آنلاین", "خرید_اینترنتی", "ارسال_سریع", "کیفیت_تضمینی",
    "خرید_مطمئن", "تخفیف_ویژه", "اینستاگرام_شاپ", "ایران", "تهران",
]


def make_hashtags(shop_name="", product_name="", extra=()):
    tags = []
    for name in (product_name, shop_name):
        if name:
            token = name.strip().replace(" ", "_").replace("،", "").replace("-", "_")
            if token:
                tags.append(token)
    tags += random.sample(HASHTAG_BASE, 5)
    tags += [t for t in extra if t]
    # یکتا و با #
    seen, out = set(), []
    for t in tags:
        t = str(t).strip().replace(" ", "_")
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def generate_caption(kind="post", template="intro", shop="", product="", desc="",
                     price="", cta="", hashtags=None):
    cta = cta or "برای سفارش دایرکت بده"
    price_line = f"💰 قیمت: {fa_price(price)}" if price else "💰 برای اطلاع از قیمت دایرکت بده"
    desc = desc or "کیفیت بالا، قیمت مناسب و ارسال سریع"
    product = product or "محصول جدید ما"

    if kind == "story":
        body = random.choice(STORY_CAPTION_TEMPLATES).format(
            product=product, desc=desc, price_line=price_line, cta=cta)
    else:
        tmpl = CAPTION_TEMPLATES.get(template, CAPTION_TEMPLATES["intro"])
        body = random.choice(tmpl).format(
            product=product, desc=desc, price_line=price_line, cta=cta, hashtags="")
        # هشتگ‌ها فقط یک بار در انتها
    body = body.replace("{hashtags}", "").strip()
    tags = hashtags if hashtags is not None else make_hashtags(shop, product)
    tag_text = " ".join(tags)
    if tag_text not in body:
        body += "\n\n" + tag_text
    return body, tag_text


def caption_ideas(product="", desc="", price="", shop=""):
    """چند پیشنهاد کپشن برای UI"""
    ideas = []
    for tpl in random.sample(list(CAPTION_TEMPLATES.keys()), 3):
        cap, tags = generate_caption("post", tpl, shop=shop, product=product,
                                     desc=desc, price=price)
        ideas.append({"template": tpl, "caption": cap, "hashtags": tags})
    return ideas


def random_tip():
    return random.choice(TIPS)


def random_quote():
    return random.choice(QUOTES)


def random_question():
    return random.choice(QUESTIONS)

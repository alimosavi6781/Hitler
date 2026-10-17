# -*- coding: utf-8 -*-
"""موتور خبر: دریافت RSS از منابع فارسی/جهانی، دسته‌بندی و ساخت کپشن خبری"""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import db

TEHRAN = ZoneInfo("Asia/Tehran")

CATEGORY_KEYWORDS = {
    "هوش مصنوعی": ["هوش مصنوعی", "چت‌جی‌پی‌تی", "chatgpt", "ChatGPT", "GPT", "OpenAI",
                   "انتروپیک", "Anthropic", "کلود", "Claude", "جمینی", "Gemini", "مدل زبانی",
                   "مدل‌های زبانی", "ربات", "رباتیک", "یادگیری ماشین", "AI", "جمنای",
                   "دیتاسنتر", "تراشه هوش مصنوعی", "انویدیا", "Nvidia", "متا",
                   "مایکروسافت", "الگوریتم", "گوگل دیپ‌مایند", "DeepMind", "مدل هوش مصنوعی"],
    "سیاسی": ["سیاست", "دولت", "مجلس", "انتخابات", "وزیر", "رئیس‌جمهور", "رئیس جمهور",
              "دیپلماسی", "مذاکره", "سفیر", "تحریم", "جنگ", "حمله", "ارتش", "سپاه",
              "ترامپ", "نتانیاهو", "اسرائیل", "غزه", "آتش‌بس", "آتش بس", "وزارت",
              "توافق", "معاهده", "بمب", "موشک", "دفاع", "خارجی", "اقلیم", "تنش",
              "نظامی", "پنتاگون", "خلیج فارس", "تنگه هرمز", "برجام", "قاآنی", "عراقچی"],
    "اقتصادی": ["اقتصاد", "ارز", "دلار", "طلا", "نفت", "بورس", "بانک", "تورم",
                "قیمت", "بودجه", "بازار", "سهام", "گمرک", "تجارت", "صادرات",
                "واردات", "سوخت", "بنزین", "پول", "یارانه", "رمزارز", "بیت‌کوین"],
    "ورزشی": ["فوتبال", "ورزش", "لیگ", "استقلال", "پرسپولیس", "تیم ملی", "جام جهانی",
              "المپیک", "والیبال", "کشتی", "مسی", "رونالدو", "قهرمانی", "داور"],
    "فناوری": ["هوش مصنوعی", "تکنولوژی", "فناوری", "فضا", "ماهواره", "اینترنت",
               "ربات", "نرم‌افزار", "دیجیتال", "علمی", "پزشکی", "دانشگاه", "تحقیق",
               "ناسا", "اسپیس", "استارلینک", "نوآوری"],
    "فرهنگی": ["سینما", "فیلم", "هنر", "موزه", "کتاب", "موسیقی", "جشنواره", "میراث",
               "بازیگر", "تئاتر", "کن",
               "سینمایی"],
    "حوادث": ["زلزله", "سیل", "آتش‌سوزی", "آتش سوزی", "تصادف", "حادثه", "انفجار",
              "فوت", "جان باخت", "مفقود", "سقوط"],
}
BREAKING_WORDS = ["فوری", "لحظاتی پیش", "دقایقی پیش", "breaking", "BREAKING", "عاجل"]

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def fa_to_en(text):
    out = []
    for ch in str(text):
        out.append(str(FA_DIGITS.index(ch)) if ch in FA_DIGITS else ch)
    return "".join(out)


NUMBER_RE = re.compile(
    r"([\d۰-۹][\d۰-۹٬,\.]*[\d۰-۹]?)\s*"
    r"(هزار|میلیون|میلیارد)?\s*"
    r"(٪|درصد|تومان|ریال|دلار|یورو|ریشتر|نفر|کیلومتر|کیلو|تن|بشکه|واحد|دستگاه|درجه|مگاوات|متر|سانتی‌متر)?",
    re.UNICODE)


def extract_numbers(text, limit=3):
    """استخراج اعداد کلیدی خبر همراه واحدشان (برای قالب آماری)"""
    text = text or ""
    found = []
    for m in NUMBER_RE.finditer(text):
        num = fa_to_en(m.group(1)).replace("٬", ",")
        scale = m.group(2)
        unit = m.group(3) or ""
        if scale:
            num = num + " " + scale
        if not unit and len(num.replace(",", "").replace(".", "")) == 4:
            continue  # احتمالاً سال میلادی/شمسی است
        found.append({"number": num, "unit": unit})
        if len(found) >= limit:
            break
    return found


def extract_quotes(text, limit=2):
    """استخراج نقل‌قول‌های داخل گیومه از متن خبر (برای قالب نقل‌قول)"""
    text = text or ""
    out = []
    for m in re.finditer(r"«([^»]{8,220})»", text):
        out.append(m.group(1).strip())
        if len(out) >= limit:
            break
    if not out:
        for m in re.finditer(r'"([^"]{8,220})"', text):
            out.append(m.group(1).strip())
            if len(out) >= limit:
                break
    return out


def template_data(item, template="auto"):
    """انتخاب هوشمند قالب + داده‌های لازم برای رندر"""
    full = ((item.get("summary") or "") + " " + (item.get("headline") or ""))
    quotes = extract_quotes(full)
    stats = extract_numbers(full)
    if template == "auto":
        template = "quote" if quotes else ("stats" if len(stats) >= 2 else "standard")
    return template, stats, quotes

CATEGORY_COLORS = {
    "هوش مصنوعی": ("#6D28D9", "#312E81", "#C4B5FD"),
    "سیاسی": ("#B91C1C", "#7F1D1D", "#FCA5A5"),
    "اقتصادی": ("#B45309", "#78350F", "#FCD34D"),
    "ورزشی": ("#047857", "#064E3B", "#6EE7B7"),
    "فناوری": ("#1D4ED8", "#312E81", "#93C5FD"),
    "فرهنگی": ("#BE185D", "#701A75", "#F9A8D4"),
    "حوادث": ("#C2410C", "#7C2D12", "#FDBA74"),
    "عمومی": ("#1E3A8A", "#0F172A", "#93C5FD"),
}


def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_summary(text, max_len=260):
    text = strip_html(text)
    text = text.replace("&nbsp;", " ")
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def categorize(text):
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in text for w in words):
            return cat
    return "عمومی"


def is_breaking(text):
    return any(w in (text or "") for w in BREAKING_WORDS)


def parse_rss(xml_text):
    """استخراج آیتم‌های خبر از XML فید"""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for node in root.iter("item"):
        title = strip_html(node.findtext("title", ""))
        if not title:
            continue
        link = node.findtext("link", "") or ""
        desc = strip_html(node.findtext("description", ""))
        pub = node.findtext("pubDate", "") or node.findtext("published", "") or ""
        image_url = ""
        media = node.find("{http://search.yahoo.com/mrss/}content")
        if media is not None:
            image_url = media.get("url", "")
        if not image_url:
            enc = node.find("enclosure")
            if enc is not None:
                image_url = enc.get("url", "")
        items.append({
            "headline": title,
            "summary": clean_summary(desc, 300),
            "link": link.strip(),
            "pub_date": pub,
            "image_url": image_url,
        })
    return items


def fetch_feed(url, source_name, category_hint=""):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; InstaManager/1.0)",
               "Accept": "application/rss+xml, application/xml, text/xml, */*"}
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    items = parse_rss(r.content if isinstance(r.content, bytes) else r.text)
    out = []
    for it in items[:15]:
        cat = category_hint if category_hint in ("ایران", "جهان") and not category_hint == "" else ""
        if not cat:
            cat = categorize(it["headline"] + " " + it["summary"])
        out.append({
            "headline": it["headline"],
            "summary": it["summary"],
            "link": it["link"],
            "source": source_name,
            "category": cat,
            "image_url": it["image_url"],
            "published_at": parse_date(it["pub_date"]),
        })
    return out


def parse_date(pub):
    if not pub:
        return datetime.now(TEHRAN).strftime("%Y-%m-%d %H:%M:%S")
    pub = pub.strip()
    try:
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(pub, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TEHRAN)
                return dt.astimezone(TEHRAN).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
    except Exception:
        pass
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", pub)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)} 00:00:00"
    return datetime.now(TEHRAN).strftime("%Y-%m-%d %H:%M:%S")


def fetch_all():
    """دریافت از همه منابع فعال و ذخیره اخبار جدید"""
    stats = {"fetched": 0, "new": 0, "errors": []}
    for src in db.get_news_sources():
        if not src["enabled"]:
            continue
        try:
            items = fetch_feed(src["url"], src["name"], src["category"] or "")
            stats["fetched"] += len(items)
            for it in items:
                nid = db.add_news(
                    it["headline"], it["summary"], it["link"], it["source"],
                    it["category"], image_path="", published_at=it["published_at"],
                    hash_key=hashlib.md5(it["headline"].encode("utf-8")).hexdigest(),
                )
                if nid:
                    stats["new"] += 1
        except Exception as e:
            stats["errors"].append(src["name"])
    return stats


def top_unused(limit=6, prefer_breaking=True):
    news = db.get_news(limit=100, unused_only=True)
    if not news:
        return []
    breaking = [n for n in news if is_breaking(n["headline"] + " " + n["summary"])]
    rest = [n for n in news if n not in breaking]
    picked = (breaking + rest)[:limit] if prefer_breaking else news[:limit]
    return picked


def news_caption(news, shop_name="", include_link=True):
    headline = news["headline"].strip()
    summary = news.get("summary") or ""
    source = news.get("source") or "منبع خبری"
    parts = []
    if is_breaking(headline + " " + summary):
        parts.append("🔴 خبر فوری")
    parts.append(headline)
    if summary:
        parts.append(summary)
    if include_link and news.get("link"):
        parts.append(f"مشروح خبر: {news['link']}")
    parts.append(f"منبع: {source}")
    cat = str(news.get("category", "عمومی")).replace(" ", "_")
    tags = ["#خبر", "#اخبار_روز", f"#اخبار_{cat}"]
    if is_breaking(headline + " " + summary):
        tags.insert(0, "#خبر_فوری")
    if shop_name:
        tags.append("#" + shop_name.strip().replace(" ", "_"))
    return "\n\n".join(parts).strip(), " ".join(dict.fromkeys(tags))


def seed_ai_news():
    """بارگذاری مجموعه خبر واقعی هوش مصنوعی (دریافت‌شده ۱۷ اوت ۲۰۲۶) برای دموی اولیه"""
    if db.get_setting("seeded_ai_news") == "1":
        return
    db.set_setting("seeded_ai_news", "1")
    items = [
        ("OpenAI introduces ‘Ultrafast,’ a new mode that makes GPT-5.6 Sol work at 14x the speed",
         "OpenAI حالت فوق‌سریع جدیدی معرفی کرد که مدل GPT-5.6 Sol را با سرعت ۱۴ برابر اجرا می‌کند؛ جهشی بزرگ برای پاسخ‌گویی لحظه‌ای.",
         "https://techcrunch.com/2026/08/13/openai-introduces-ultrafast-a-new-mode-that-makes-gpt-5-6-sol-work-at-14x-the-speed/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-13 19:22:40"),
        ("Nvidia investing $1.5B in SoftBank data center developer behind OpenAI project",
         "انویدیا ۱.۵ میلیارد دلار در توسعه‌دهنده دیتاسنترهای سافت‌بانک سرمایه‌گذاری می‌کند؛ پروژه‌ای که زیرساخت مدل‌های OpenAI را تأمین می‌کند.",
         "https://techcrunch.com/2026/08/17/nvidia-investing-1-5b-in-softbank-data-center-developer-behind-openai-project/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-17 15:16:24"),
        ("Groq raises $350M to fuel its pivot from AI chips to neocloud",
         "استارتاپ تراشه‌ساز Groq در مسیر چرخش از تراشه‌های AI به سرویس ابری «نئوکلود»، ۳۵۰ میلیون دلار جذب کرد.",
         "https://techcrunch.com/2026/08/17/groq-raises-350m-to-fuel-its-pivot-from-ai-chips-to-neocloud/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-17 16:15:12"),
        ("Stripe will reportedly acquire AI gateway startup OpenRouter for $7B+",
         "گزارش‌ها از خرید استارتاپ OpenRouter توسط استرایپ به ارزش بیش از ۷ میلیارد دلار حکایت دارد؛ دروازه دسترسی یکپارچه به مدل‌های AI.",
         "https://techcrunch.com/2026/08/16/stripe-will-reportedly-acquire-ai-gateway-startup-openrouter-for-7b/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-16 20:57:04"),
        ("Anthropic CEO says AI backlash is ‘fundamentally a crisis of trust’",
         "مدیرعامل Anthropic می‌گوید واکنش منفی به هوش مصنوعی در اصل «بحران اعتماد» است و شفافیت را راه‌حل می‌داند.",
         "https://techcrunch.com/2026/08/16/anthropic-ceo-says-ai-backlash-is-fundamentally-a-crisis-of-trust/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-16 16:53:51"),
        ("IBM partners with OpenAI to bolster enterprise AI push",
         "آی‌بی‌ام برای تقویت حضور هوش مصنوعی سازمانی، با OpenAI شریک می‌شود؛ ترکیب زیرساخت سازمانی با مدل‌های پیشرو.",
         "https://techcrunch.com/2026/08/13/ibm-partners-with-openai-to-bolster-enterprise-ai-push/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-13 19:19:49"),
        ("Databricks wanted to raise $1B, investors wanted $15B. It settled on $5B at a $190B valuation.",
         "دیتابرکس در دور جدید سرمایه‌گذاری، با ارزش‌گذاری ۱۹۰ میلیارد دلاری، ۵ میلیارد دلار جذب کرد؛ نشانه‌ای از اشتهای عظیم بازار برای زیرساخت داده و AI.",
         "https://techcrunch.com/2026/08/13/databricks-wanted-to-raise-1b-investors-wanted-15b-it-settled-on-5b-at-a-190b-valuation/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-13 20:14:39"),
        ("Amazon, which started off selling books, is destroying rare texts to train AI",
         "آمازون که روزی فروشنده کتاب بود، حالا برای آموزش مدل‌های هوش مصنوعی کتاب‌های نایاب را نابود می‌کند؛ گزارش جنجالی درباره هزینه پنهان آموزش مدل‌ها.",
         "https://techcrunch.com/2026/08/17/amazon-once-an-online-bookseller-is-destroying-rare-books-to-train-ai-models/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-17 16:38:44"),
        ("Google will now allow users to remove visible watermark from its AI generations",
         "گوگل اعلام کرد کاربران می‌توانند واترمارک قابل‌مشاهده تصاویر تولیدشده با هوش مصنوعی این شرکت را حذف کنند؛ تصمیمی بحث‌برانگیز درباره شفافیت محتوا.",
         "https://techcrunch.com/2026/08/14/google-will-now-allow-users-to-remove-visible-watermark-from-its-ai-generations/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-14 16:13:40"),
        ("SpaceX officially closes its Cursor acquisition",
         "اسپیس‌ایکس رسماً خرید استارتاپ Cursor را نهایی کرد؛ ادغامی غیرمنتظره میان صنعت فضایی و ابزارهای برنامه‌نویسی با هوش مصنوعی.",
         "https://techcrunch.com/2026/08/15/spacex-officially-closes-its-cursor-acquisition/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-15 16:30:00"),
        ("Wispr raises $280M at $2B valuation as it looks beyond dictation",
         "استارتاپ Wispr با ارزش‌گذاری ۲ میلیارد دلاری، ۲۸۰ میلیون دلار جذب کرد تا از تشخیص گفتار فراتر برود؛ نسل جدید رابط مغز و ماشین.",
         "https://techcrunch.com/2026/08/17/wispr-raises-280m-at-2b-valuation-as-it-looks-beyond-dictation/",
         "تک‌کرانچ", "هوش مصنوعی", "2026-08-17 13:10:05"),
        ("Iran joins founding members of global AI organization",
         "ایران به جمع اعضای مؤسس یک سازمان جهانی هوش مصنوعی پیوست؛ حضوری تازه در حکمرانی بین‌المللی AI.",
         "https://news.google.com/rss/articles/CBMiigFBVV95cUxORnFVYURoMXozUWwzNGJJSWswWkViX05qem5icDhqSWRKLWRQbDRVSHBrN051Q0FoN1BxbUxjY0RONjhjenZXYTcwOHBVYjdGU3VVMzR2X190QldER2FoWUl6eTk0Y3BFMlFsdkpZRWxoZkJXb0N4TU1yemJfVzdPRGpkMm0",
         "گوگل‌نیوز", "هوش مصنوعی", "2026-08-15 11:38:35"),
    ]
    added = 0
    for headline, summary, link, source, cat, pub in items:
        nid = db.add_news(headline, summary, link, source, cat,
                          published_at=pub,
                          hash_key=hashlib.md5(headline.encode("utf-8")).hexdigest())
        if nid:
            added += 1
    if added:
        db.log_activity(f"🤖 {added} خبر واقعی هوش مصنوعی بارگذاری شد — در تب «اخبار» ببین.")
    return added


def seed_real_news():
    """بارگذاری یک مجموعه خبر واقعی (دریافت‌شده ۱۷ اوت ۲۰۲۶) برای دموی اولیه"""
    if db.get_setting("seeded_news") == "1":
        return
    db.set_setting("seeded_news", "1")
    items = [
        ("ترامپ: اگر عمان در رابطه با ایران سر راهمان قرار بگیرد، بمبارانش می‌کنیم",
         "رئیس‌جمهور آمریکا در تازه‌ترین اظهارنظر درباره بحران منطقه، به عمان درباره نقش‌آفرینی در مسیر ایران هشدار داد.",
         "https://www.bbc.com/persian/articles/cvg9y7j1360o", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 18:29:00"),
        ("«تماس پشت پرده سپاه و آمریکا»؛ ترامپ و سخنگوی اقلیم کردستان تایید کردند و ایران تکذیب",
         "گزارش‌ها از تماس‌های پنهانی میان سپاه پاسداران و آمریکا حکایت دارد؛ مقام‌های آمریکایی و اقلیم کردستان آن را تأیید و تهران تکذیب کرده است.",
         "https://www.bbc.com/persian/articles/c0ej34p72dyo", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 13:35:00"),
        ("بازداشت دو طراح گرافیک در تهران؛ نزدیکانشان از حضور دو دیپلمات فرانسوی در جلسه‌ای که به بازداشت آنها انجامید خبر دادند",
         "نزدیکان دو طراح گرافیک بازداشت‌شده در تهران می‌گویند در جلسه‌ای که به بازداشت آنها انجامید، دو دیپلمات فرانسوی نیز حضور داشته‌اند.",
         "https://www.bbc.com/persian/articles/c4g6mk3jd6go", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 17:33:00"),
        ("لکه نفتی قشم از کجا آمد و چه خطری برای محیط‌زیست دارد؟",
         "پیدایش لکه نفتی در سواحل قشم نگرانی‌ها درباره آسیب به اکوسیستم دریایی و معیشت مردم جزیره را افزایش داده است.",
         "https://www.bbc.com/persian/articles/cy077n8l9kxo", "بی‌بی‌سی فارسی", "حوادث", "2026-08-17 15:33:00"),
        ("دیدار فرستاده ترامپ با نتانیاهو پس از گفتگو با حماس درباره طرح صلح غزه",
         "فرستاده ویژه آمریکا پس از گفتگو با رهبران حماس درباره طرح صلح، با نخست‌وزیر اسرائیل دیدار کرد.",
         "https://www.bbc.com/persian/articles/cn8nm51elx7o", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 14:48:00"),
        ("قمار بر سر زمان؛ ایران و آمریکا در آستانه مرحله‌ای تازه از جنگ؟",
         "با نزدیک‌شدن به پایان مهلت‌های تعیین‌شده، پرسش اصلی این است که آیا ایران و آمریکا از لبه پرتگاه فاصله می‌گیرند یا وارد مرحله تازه‌ای از درگیری می‌شوند.",
         "https://www.bbc.com/persian/articles/cjej83y704do", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 07:19:00"),
        ("معاون سپاه: تنگه هرمز زمانی باز می‌شود که آمریکا معاهده اسلام‌آباد را عملی کند",
         "مقام ارشد سپاه پاسداران بازگشایی تنگه هرمز را مشروط به اجرای معاهده اسلام‌آباد از سوی آمریکا دانست.",
         "https://www.bbc.com/persian/articles/c4gwkxqy0k1o", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 11:35:00"),
        ("ایران می‌گوید درباره به‌رسمیت‌شناختن حکومت طالبان هنوز به جمع‌بندی نرسیده است",
         "وزارت خارجه ایران اعلام کرد درباره شناسایی رسمی حکومت طالبان در افغانستان هنوز تصمیم نهایی گرفته نشده است.",
         "https://www.bbc.com/persian/articles/cy45zk52g2no", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-17 18:36:00"),
        ("ادعای «اسارت» خلبانان ایرانی؛ قطر تکذیب کرد، ایران خواستار ورود تیم کارشناسی شد",
         "پس از ادعاهایی درباره سرنوشت خلبانان ایرانی، قطر این ادعاها را تکذیب کرد و تهران خواستار اعزام تیم کارشناسی شد.",
         "https://www.bbc.com/persian/articles/cp3005ngey9o", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-16 11:10:00"),
        ("آنچه گذشت؛ قالیباف: تفاهم‌نامه، سند پیروزی در میدان دیپلماسی است",
         "رئیس مجلس شورای اسلامی تفاهم‌نامه اخیر را دستاوردی در عرصه دیپلماسی توصیف کرد و جزئیات آن را تشریح کرد.",
         "https://www.bbc.co.uk/persian/live/c5wymm0339j8t", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-16 22:00:00"),
        ("آیا عراق به‌تدریج از ایران فاصله می‌گیرد؟",
         "تحلیل‌گران با اشاره به تحولات اخیر در روابط بغداد و تهران، از نشانه‌های فاصله‌گیری تدریجی عراق از ایران می‌گویند.",
         "https://www.bbc.com/persian/articles/cly55wgynnjo", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-16 05:11:00"),
        ("در حالی که تصاویر زنده از ساختمان صداوسیمای جمهوری اسلامی در حال پخش بود، اسرائیل این ساختمان را هدف قرار داد و پخش زنده شبکه خبر به‌طور ناگهانی قطع شد",
         "شبکه خبر در جریان پخش زنده، هدف حمله قرار گرفت و پخش آن به‌طور ناگهانی قطع شد.",
         "https://news.google.com/rss/articles/CBMijgVBVV95cUxNdmNDN09BWXhQc0FIcDNTeEtMblgtdE9zaWZ2RlFac3g1eGNpN0R0U3FtNS05LVVyODhvU0dFR3RKUDlxNG9Vb3VuVUZ6TnV5dmRKejMxd3JfazJ6RWpxb3lWbnVpUGxzUFFLS0lvcXNudHpSbkV6eUZ0UWIzejVMcDhOT3hDcFB1cnNMcDhoU2lPNXU1RmpReW5jcXZWbm1aSXRGeTFQWlJISjVHa0xpcUZ2bER2Z2xrNE50SDFSeXVrZVQtNGpCb2hnZi1ES2hHTFY4eE8yb1B0cG41M19RYmRJdlF3UkpTMFFiVHF2RHlzV3pZMnl2cVNfRkFrZlc3WkFlanVJemJkeVZjdkRQY1JmRXdJZnZvY015X2ZMaGpfU052ZFlXWXVzTm95dS1xbnNiTTBzR3AzeWJEVlNPTlhRa1FpRzg3Um80MXl6cUMzU1lOQXB5d056WGxNaVV3U1pNNi1wNTJhVWdsZ2xQYnhjUm9sdURUZExtZDlPVEpOOU9YcUxNRU5qY093dW9JVUNHT2hXd0tmbFZWRjg1V05ndTh1UjZWbVBPT3ByU2xVOEtyWXVnUmxEYmVkUjFCUnQtNy1DSGxEQjN4UG5MbHNGTXFPdno5YTBYOWIxcFd3RVRiX0kyV1BsU1VjTUtnVTVFUTlfel81Y1p4aURONXZjcmF4WlBPWmxPdThVVllIa01oZWJ4N1prQzlGZVBSeFBMbkRnaElXZ1RjallnVFo4VzRxRkFlQ2RmMmcyM3BDNmFRS2FOSzMyX1VuV1FEYmdEVEtNMXFhSGprQUc3Sk1pbDZLYy1XbnV2R2tTRFVnVTlGN0JNNjRsUk05RHEweUJ4TndRUC1ZQTdMWHc", "گوگل‌نیوز", "سیاسی", "2026-08-17 19:11:00"),
        ("عراقچی در واکنش به عملیات پرچم دروغین در کردستان عراق: دوستان کرد ما هوشیار باشند",
         "وزیر امور خارجه در واکنش به خبر حمله به دفتر نخست‌وزیر اقلیم کردستان، هدف این اقدام را ایجاد اختلاف میان همسایگان دانست.",
         "https://www.irna.ir/news/86238365", "ایرنا", "سیاسی", "2026-08-17 18:59:00"),
        ("رئیس دفتر سیاسی حماس گروه‌های فلسطینی را در جریان مذاکرات خود با میانجی‌ها قرار داد",
         "رئیس دفتر سیاسی حماس با رهبران گروه‌های فلسطینی دیدار و آنان را در جریان آخرین تحولات سیاسی و میدانی قرار داد.",
         "https://www.irna.ir/news/86238347", "ایرنا", "سیاسی", "2026-08-17 19:06:00"),
        ("معاون رئیس‌جمهور: ثبت جهانی آثار، صدور شناسنامه تمدن ایران در نظام حقوق بین‌الملل است",
         "معاون راهبردی رئیس‌جمهور بر ضرورت پیوند میان جوانان و میراث ملموس و ناملموس کشور تأکید کرد.",
         "https://www.irna.ir/news/86238371", "ایرنا", "فرهنگی", "2026-08-17 19:09:00"),
        ("بختیاری‌زاده: استقلال با وجود برد در هفته نخست، ضعف‌هایی دارد",
         "سرمربی استقلال با اشاره به پیروزی تیمش در هفته نخست لیگ برتر، از وجود نقاط ضعفی گفت که باید برطرف شود.",
         "https://www.irna.ir/news/86238305", "ایرنا", "ورزشی", "2026-08-17 18:50:00"),
        ("لکه نفتی قشم؛ جزئیات تازه از منشأ آلودگی و اقدامات پاکسازی",
         "مسئولان محیط زیست از آغاز عملیات پاکسازی سواحل قشم و بررسی منشأ آلودگی نفتی خبر دادند.",
         "https://www.irna.ir/news/86238000", "ایرنا", "حوادث", "2026-08-17 16:20:00"),
        ("تهدید ترامپ، تنگه هرمز و نقش چین؛ سه روایت از رسانه‌های آمریکا",
         "رسانه‌های آمریکایی با سه روایت متفاوت، ابعاد تهدیدهای اخیر درباره تنگه هرمز و نقش چین را بررسی کرده‌اند.",
         "https://www.bbc.com/persian/articles/czxe2rek35eo", "بی‌بی‌سی فارسی", "سیاسی", "2026-08-13 09:57:00"),
    ]
    added = 0
    for headline, summary, link, source, cat, pub in items:
        nid = db.add_news(headline, summary, link, source, cat,
                          published_at=pub,
                          hash_key=hashlib.md5(headline.encode("utf-8")).hexdigest())
        if nid:
            added += 1
    if added:
        db.log_activity(f"📰 {added} خبر واقعی امروز (ایران و جهان) بارگذاری شد — در تب «اخبار» ببین.")
    return added

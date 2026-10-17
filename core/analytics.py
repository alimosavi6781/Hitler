# -*- coding: utf-8 -*-
"""آنالیز پیج: جمع‌آوری اینسایت، ذخیره تاریخچه و تولید پیشنهاد رشد"""
from datetime import datetime

from . import db
from .content import fa_num
from .ig_api import IGClient, IGError


def fetch_and_store(token, ig_id):
    """اینسیت امروز را از API بگیر و در دیتابیس ذخیره کن"""
    ig = IGClient(token, ig_id)
    summary = ig.account_summary()
    today = datetime.now().strftime("%Y-%m-%d")

    reach = impressions = profile_views = likes = comments = None
    try:
        for metric in ig.account_insights(days=3):
            name = metric.get("name")
            values = [v.get("value", 0) for v in metric.get("values", [])]
            total = sum(values) if values else None
            if name == "reach":
                reach = total
            elif name == "impressions":
                impressions = total
            elif name == "profile_views":
                profile_views = total
    except IGError:
        pass

    try:
        media = ig.recent_media(limit=25)
        if media:
            likes = sum(m.get("like_count") or 0 for m in media)
            comments = sum(m.get("comments_count") or 0 for m in media)
    except IGError:
        pass

    followers = summary.get("followers_count")
    following = summary.get("follows_count")
    media_count = summary.get("media_count")
    er = None
    if reach and followers:
        er = round(100.0 * (likes or 0) / reach, 2) if likes is not None else None

    db.upsert_metric(
        today,
        followers=followers,
        following=following,
        media_count=media_count,
        reach=reach,
        impressions=impressions,
        profile_views=profile_views,
        likes=likes,
        comments=comments,
        engagement_rate=er,
        source="api",
    )
    db.log_activity(f"📊 اینسایت امروز ذخیره شد — فالوور: {fa_num(followers or 0)}")
    return summary


def _growth_rate(metrics):
    if len(metrics) < 2:
        return None
    first = metrics[0].get("followers")
    last = metrics[-1].get("followers")
    if not first or not last:
        return None
    days = max(1, len(metrics) - 1)
    return round(100.0 * ((last / first) ** (1 / max(days, 1)) - 1), 2)


def _best_hours(token, ig_id):
    try:
        ig = IGClient(token, ig_id)
        data = ig.online_followers()
        hours = [0] * 24
        for item in data:
            for v in item.get("values", []):
                for h, count in (v.get("value") or {}).items():
                    try:
                        hours[int(h)] = int(count)
                    except (ValueError, TypeError):
                        pass
        if not any(hours):
            return None
        # ۳ ساعت برتر
        best = sorted(range(24), key=lambda i: -hours[i])[:3]
        return [{"hour": h, "count": hours[h]} for h in best]
    except Exception:
        return None


def recommendations(use_api=False, token="", ig_id=""):
    """تولید پیشنهادهای هوشمند رشد پیج"""
    out = []
    metrics = db.get_metrics(60)
    settings = db.all_settings()

    if use_api and token and ig_id:
        hours = _best_hours(token, ig_id)
        if hours:
            hh = "، ".join(fa_num(f"{h['hour']:02d}:00") for h in hours)
            out.append({
                "icon": "⏰", "title": "بهترین ساعت انتشار",
                "text": f"بیشترین فالوورهای آنلاین پیج شما در ساعت‌های {hh} است. "
                        f"پست‌ها را در این بازه منتشر کن تا ریچ بالاتری بگیری.",
                "priority": "high",
            })
        out.append({
            "icon": "📊", "title": "اینسیت خودکار فعال است",
            "text": "هر شب ساعت ۲۳:۴۵ آمار پیج به‌صورت خودکار ذخیره می‌شود و روند رشد را در تب آنالیز می‌بینی.",
            "priority": "info",
        })
    else:
        out.append({
            "icon": "🔌", "title": "اتصال به API متا",
            "text": "برای آنالیز خودکار و انتشار مستقیم، اکانت اینستاگرامت را از تب «تنظیمات ← اتصال اینستاگرام» وصل کن. "
                    "راهنمای قدم‌به‌قدم همان‌جاست.",
            "priority": "high",
        })

    rate = _growth_rate(metrics)
    if rate is not None:
        sign = "افزایش" if rate > 0 else "کاهش"
        verdict = ("عالی! روند رو به رشدی" if rate > 1 else
                   "خوبه؛ می‌تونی با استوری بیشتر سرعتش رو بیشتر کنی" if rate > 0 else
                   "نیاز به اقدام جدی")
        out.append({
            "icon": "📈", "title": f"نرخ رشد روزانه فالوور: {sign} {fa_num(abs(rate))}٪",
            "text": f"{verdict}. " + ("همین ریتم محتوا را ادامه بده." if rate > 1 else
                                      "پست تعاملی (سوال/نظرسنجی) و استوری روزانه را جدی بگیر."),
            "priority": "high" if rate <= 0 else "normal",
        })

    recent = db.get_posts(["published", "ready", "scheduled"])[:30]
    stories = [p for p in recent if p["kind"] == "story"]
    posts = [p for p in recent if p["kind"] == "post"]
    if posts:
        avg_er_est = None
        out.append({
            "icon": "🗓️", "title": "نظم انتشار",
            "text": f"{fa_num(len(posts))} پست و {fa_num(len(stories))} استوری در صف انتشار داری. "
                    "ثبات در انتشار مهم‌ترین عامل رشد ارگانیک است — تقویم را خالی نگذار.",
            "priority": "normal",
        })
    else:
        out.append({
            "icon": "🚀", "title": "هنوز محتوایی زمان‌بندی نکرده‌ای",
            "text": "از تب «ساخت پست» شروع کن. پیشنهاد ما: ۱ پست محصول + ۲ استوری در روز.",
            "priority": "high",
        })

    out.append({
        "icon": "💬", "title": "پاسخ‌گویی در ساعت اول",
        "text": "به ۱۰۰٪ کامنت‌های ۶۰ دقیقه‌ی اول پاسخ بده؛ الگوریتم اینستاگرام این تعامل را دو برابر حساب می‌کند.",
        "priority": "normal",
    })
    out.append({
        "icon": "🎞️", "title": "ریلز = موتور رشد",
        "text": "هفته‌ای حداقل ۱ ریلز ۱۵ تا ۳۰ ثانیه‌ای از محصولاتت بساز (نمای نزدیک، بسته‌بندی، پشت‌صحنه). "
                "ریلز بیشترین دسترسی ارگانیک را دارد.",
        "priority": "normal",
    })
    return out


def weekly_report_text():
    """متن گزارش هفتگی ساده"""
    metrics = db.get_metrics(7)
    if not metrics:
        return "هنوز داده‌ای ثبت نشده. از تب آنالیز، آمار فالوور را ثبت یا API را وصل کن."
    last = metrics[-1]
    first = metrics[0]
    f = last.get("followers") or 0
    f0 = first.get("followers") or 0
    delta = f - f0
    return (
        f"گزارش هفتگی پیج:\n"
        f"فالوور فعلی: {fa_num(f)} (تغییر: {'+' if delta >= 0 else ''}{fa_num(delta)})\n"
        f"میانگین ریچ: {fa_num(int(sum(m.get('reach') or 0 for m in metrics) / len(metrics)))}\n"
        f"میانگین بازدید پروفایل: {fa_num(int(sum(m.get('profile_views') or 0 for m in metrics) / len(metrics)))}"
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سازنده فایل HTML خودبسنده راهنمای A5/A6/A7 + نسخه سبک تصویر.

خروجی‌ها:
    figures-a5-a6-a7.html             یک فایل، بدون وابستگی بیرونی (فونت و شکل‌ها درون فایل)
    figures-sheet-a5-a6-a7-small.jpg  نسخه سبک برگه تصویری برای پیام‌رسان‌ها

اجرا بعد از build_sheet.py.
"""
import base64
import html
import os

from PIL import Image

from figures import FIGURES
from content_a567 import EXERCISES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_HTML = os.path.join(HERE, "figures-a5-a6-a7.html")
SHEET = os.path.join(HERE, "figures-sheet-a5-a6-a7.jpg")
OUT_SMALL = os.path.join(HERE, "figures-sheet-a5-a6-a7-small.jpg")


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def build():
    if os.path.exists(SHEET):
        im = Image.open(SHEET)
        small = im.resize((1100, int(im.height * 1100 / im.width)), Image.LANCZOS)
        small.save(OUT_SMALL, quality=82, optimize=True, progressive=True)
        print("ساخته شد:", OUT_SMALL, small.size,
              round(os.path.getsize(OUT_SMALL) / 1024, 1), "KB")

    fonts = {w: b64(os.path.join(HERE, "fonts", "vazirmatn-arabic-%d-normal.woff2" % w))
             for w in (400, 600, 700, 800)}
    face = "\n".join(
        "@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:%d;"
        "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}" % (w, d)
        for w, d in fonts.items())

    def ex_block(ex):
        figs = "\n".join(
            '<figure class="plate">%s<figcaption>%s</figcaption></figure>'
            % (FIGURES[k]().to_svg(label=c), html.escape(c)) for k, c in ex["figures"])
        steps = "\n".join("<li>%s</li>" % html.escape(s) for s in ex["steps"])
        cues = "\n".join("<li>%s</li>" % html.escape(c) for c in ex["cues"])
        miss = "\n".join("<li>%s</li>" % html.escape(m) for m in ex["mistakes"])
        return """
<section>
  <h2><span class="code">%s</span> %s <span class="en">%s</span></h2>
  <p class="meta">%s | %s</p>
  <div class="figs">%s</div>
  <p class="h3">کدام نسخه؟</p><p class="meta">%s</p>
  <p class="h3">مراحل اجرا</p><ol class="steps">%s</ol>
  <div class="two">
    <div><p class="h3 ok">نکات کلیدی</p><ul class="do">%s</ul></div>
    <div><p class="h3 bad">اشتباهات رایج</p><ul class="dont">%s</ul></div>
  </div>
  <p class="check"><b>خودآزمایی بعد از ست:</b> %s</p>
</section>""" % (html.escape(ex["code"]), html.escape(ex["title"]), html.escape(ex["en"]),
                html.escape(ex["role"]), " · ".join(ex["specs"]), figs,
                "؛ ".join(ex["variants"]), steps, cues, miss, html.escape(ex["check"]))

    page = """<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>راهنمای تصویری A5، A6 و A7 — فایل خودبسنده</title>
<style>
%s
:root{--ink:#11151c;--dim:#4a5464;--line:#d3dae5;--amber:#9a6200;--amberbg:#fdf4e3;
--teal:#0c6f60;--tealbg:#e9f7f4;--rose:#a83535}
*{box-sizing:border-box}
body{margin:0;background:#f2f5f9;color:var(--ink);font-family:'Vazirmatn',system-ui,Tahoma,sans-serif;
line-height:1.95;font-size:16px}
.wrap{max-width:1050px;margin:0 auto;padding:0 16px 60px}
header{background:#11151c;color:#fff;padding:26px 16px;margin:0 -16px 24px}
header h1{margin:0 0 6px;font-size:1.5rem}
header p{margin:0;color:#aeb9c9;font-size:.9rem}
section{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:22px}
h2{font-size:1.15rem;margin:0 0 6px}
.code{display:inline-block;background:var(--amberbg);color:var(--amber);border:1px solid #e8d4a8;
border-radius:9px;padding:1px 10px;margin-left:6px;font-size:.9rem}
.en{font-size:.75em;color:#7b8798;direction:ltr;display:inline-block}
.meta{color:var(--dim);font-size:.88rem;margin:2px 0 12px}
.figs{display:grid;gap:12px;margin:12px 0}
@media(min-width:800px){.figs{grid-template-columns:1fr 1fr}}
.plate{margin:0;border:1px solid var(--line);border-radius:12px;padding:8px;background:#fff}
.plate svg{width:100%%;height:auto;display:block;border-radius:8px}
.plate figcaption{font-size:.78rem;color:#5b6675;text-align:center;margin-top:6px;font-weight:600}
.h3{font-weight:700;margin:14px 0 4px;font-size:.95rem}
.h3.ok{color:#187642} .h3.bad{color:var(--rose)}
ol.steps{margin:0;padding-right:20px} ol.steps li{margin-bottom:8px;color:#39404e;font-size:.92rem}
ul{margin:0;padding-right:18px} ul li{margin-bottom:7px;color:#39404e;font-size:.92rem}
.two{display:grid;gap:14px} @media(min-width:800px){.two{grid-template-columns:1fr 1fr}}
.check{background:var(--tealbg);border:1px solid #cbe9e3;border-radius:12px;padding:10px 12px;
font-size:.9rem;color:#124a41;margin:14px 0 0}
footer{color:#5b6675;font-size:.82rem;border-top:1px solid var(--line);padding-top:16px}
</style></head><body>
<div class="wrap">
<header>
  <h1>نحوه اجرای A5، A6 و A7 — راهنمای تصویری</h1>
  <p>نشر خم پشت شانه · نشر Y · چرخش خارجی کابل — این فایل خودبسنده است (فونت و شکل‌ها درون خودش) و همه‌جا باز می‌شود.</p>
</header>
%s
<footer>قوانین مشترک: تمپو ۱ ثانیه بالا · ۱ ثانیه توقف اوج · ۲ تا ۳ ثانیه پایین · آرنج با زاویه ثابت ·
دامنه تا مرز بدون درد · در صورت درد تیز، ست را تمام کن. شکل‌ها شماتیک‌اند و جایگزین آموزش حضوری نیستند.</footer>
</div></body></html>""" % (face, "".join(ex_block(e) for e in EXERCISES))

    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("ساخته شد:", OUT_HTML, round(len(page) / 1024, 1), "KB")


if __name__ == "__main__":
    build()

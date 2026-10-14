#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ساخت صفحه وب «راهنمای تصویری A5، A6 و A7» از روی figures.py و content_a567.py"""

import html
import os

from figures import FIGURES
from content_a567 import EXERCISES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "exercises-a5-a6-a7.html")
E = html.escape

ACCENT = {"AMBER": ("var(--amber)", "var(--amber-soft)"),
          "TEAL": ("var(--teal)", "var(--teal-soft)")}

CSS = """
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:400;font-display:swap;src:url('fonts/vazirmatn-arabic-400-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:500;font-display:swap;src:url('fonts/vazirmatn-arabic-500-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:600;font-display:swap;src:url('fonts/vazirmatn-arabic-600-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:700;font-display:swap;src:url('fonts/vazirmatn-arabic-700-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:800;font-display:swap;src:url('fonts/vazirmatn-arabic-800-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:400;font-display:swap;src:url('fonts/vazirmatn-latin-400-normal.woff2') format('woff2');}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:700;font-display:swap;src:url('fonts/vazirmatn-latin-700-normal.woff2') format('woff2');}
:root{--bg:#0e1014;--bg2:#141821;--card:#171c26;--card2:#1d2331;--line:#2a3242;--txt:#e8edf5;
--dim:#98a4b8;--dim2:#6f7c92;--amber:#ffb020;--amber-soft:#3a2d10;--teal:#3ad0b8;--teal-soft:#0f2e2c;
--rose:#ff6b6b;--rose-soft:#3a1a1f;--blue:#5aa9ff;--blue-soft:#132539;--ok:#4ade80;--ok-soft:#12301f;
--font:'Vazirmatn',system-ui,-apple-system,'Segoe UI',Tahoma,sans-serif}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(1100px 600px at 85% -10%,rgba(255,176,32,.10),transparent 60%),
radial-gradient(900px 500px at 5% 0%,rgba(58,208,184,.08),transparent 55%),var(--bg);
color:var(--txt);font-family:var(--font);font-size:16px;line-height:1.95;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 18px 70px}
a{color:var(--amber)}
header.hero{padding:46px 0 22px;border-bottom:1px solid var(--line);margin-bottom:26px}
.kicker{display:inline-flex;align-items:center;gap:8px;font-size:.8rem;font-weight:600;color:var(--amber);
background:var(--amber-soft);border:1px solid #4b3a12;padding:6px 13px;border-radius:999px;margin-bottom:16px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--amber);box-shadow:0 0 0 4px rgba(255,176,32,.16)}
h1{font-size:clamp(1.55rem,4.6vw,2.4rem);line-height:1.35;margin:0 0 12px;font-weight:800;letter-spacing:-.5px}
.sub{color:var(--dim);max-width:66ch;margin:0}
.chips{display:flex;flex-wrap:wrap;gap:9px;margin-top:20px}
.chip{font-size:.82rem;font-weight:600;color:var(--dim);background:var(--card);border:1px solid var(--line);padding:7px 13px;border-radius:999px}
.chip b{color:var(--txt)}
nav.toc{position:sticky;top:0;z-index:30;background:rgba(14,16,20,.86);backdrop-filter:blur(12px);
border-bottom:1px solid var(--line);margin:0 -18px 30px;padding:10px 18px;overflow-x:auto}
nav.toc ul{display:flex;gap:8px;list-style:none;margin:0;padding:0;white-space:nowrap}
nav.toc a{font-size:.82rem;font-weight:600;color:var(--dim);text-decoration:none;padding:6px 11px;border-radius:9px;display:inline-block}
nav.toc a:hover{color:var(--txt);background:var(--card2)}
section{margin-bottom:48px;scroll-margin-top:66px}
.sec-h{display:flex;align-items:center;gap:12px;margin:0 0 8px}
.sec-n{flex:0 0 auto;width:40px;height:40px;border-radius:12px;display:grid;place-items:center;
background:var(--card2);border:1px solid var(--line);font-weight:800;font-size:.95rem}
h2{font-size:clamp(1.15rem,3.2vw,1.5rem);margin:0;font-weight:800}
h3{font-size:1rem;margin:0 0 8px;font-weight:700}
.en{font-weight:500;font-size:.8em;color:var(--dim2);direction:ltr;display:inline-block}
.role{color:var(--dim);font-size:.9rem;margin:4px 0 0}
.specs{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 0}
.sp{font-size:.78rem;font-weight:600;background:var(--bg2);border:1px solid var(--line);color:var(--dim);padding:4px 10px;border-radius:8px}
.sp.key{color:var(--amber);border-color:#4b3a12;background:var(--amber-soft)}
.figgrid{display:grid;gap:14px;margin:20px 0 6px}
@media(min-width:820px){.figgrid{grid-template-columns:1fr 1fr}}
.plate{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px}
.plate svg{width:100%;height:auto;display:block;border-radius:10px}
.plate figcaption{font-size:.8rem;color:var(--dim2);margin-top:9px;text-align:center;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:14px}
ol.steps{margin:0;padding:0;list-style:none;counter-reset:s}
ol.steps li{position:relative;padding-right:44px;margin-bottom:12px;font-size:.94rem;color:var(--dim);counter-increment:s}
ol.steps li::before{content:counter(s);position:absolute;right:0;top:.15em;width:28px;height:28px;
border-radius:9px;display:grid;place-items:center;background:var(--card2);border:1px solid var(--line);
color:var(--amber);font-weight:800;font-size:.82rem}
ol.steps li b{color:var(--txt)}
ul.clean{list-style:none;padding:0;margin:0}
ul.clean li{position:relative;padding-right:24px;margin-bottom:9px;font-size:.93rem;color:var(--dim)}
ul.clean li::before{content:"";position:absolute;right:6px;top:.72em;width:7px;height:7px;border-radius:2px;background:var(--dim2)}
ul.do li::before{background:var(--ok)}
ul.dont li::before{background:var(--rose)}
ul.clean li b{color:var(--txt)}
.callout{border-radius:16px;padding:16px 18px;border:1px solid var(--line);background:var(--card);margin-top:14px}
.callout.amber{border-color:#4b3a12;background:linear-gradient(90deg,var(--amber-soft),transparent 75%)}
.callout.teal{border-color:#14453f;background:linear-gradient(90deg,var(--teal-soft),transparent 75%)}
.callout.rose{border-color:#4d2229;background:linear-gradient(90deg,var(--rose-soft),transparent 75%)}
.callout h3{font-size:.95rem;margin-bottom:6px}
.callout p{margin:0;color:var(--dim);font-size:.92rem}
.two{display:grid;gap:14px;margin-top:14px}
@media(min-width:820px){.two{grid-template-columns:1fr 1fr}}
footer{border-top:1px solid var(--line);padding-top:20px;color:var(--dim2);font-size:.85rem}
.toolbar{display:flex;gap:9px;flex-wrap:wrap;margin:0 0 18px}
.toolbar button{background:var(--card);border:1px solid var(--line);color:var(--dim);font-family:var(--font);
font-size:.82rem;font-weight:600;padding:9px 15px;border-radius:10px;cursor:pointer}
.toolbar button:hover{color:var(--txt)}
@media print{
 :root{--bg:#fff;--card:#fff;--card2:#f4f6fa;--line:#ccd3de;--txt:#11151c;--dim:#3c4655;--dim2:#5b6675;
 --amber:#9a6200;--amber-soft:#fdf4e3;--teal:#0c6f60;--teal-soft:#e9f7f4;--rose:#a83535;--rose-soft:#fdeeee}
 body{background:#fff;font-size:11pt}
 nav.toc,.toolbar{display:none!important}
 section{break-inside:avoid-page}
 .plate,.card,.callout{break-inside:avoid}
}
"""


def render_exercise(ex):
    fg, bg = ACCENT[ex["accent"]]
    figs = "\n".join(
        '<figure class="plate">%s<figcaption>%s</figcaption></figure>'
        % (FIGURES[key]().to_svg(label=caption), E(caption))
        for key, caption in ex["figures"])
    specs = "\n".join(
        '<span class="sp%s">%s</span>' % (" key" if i == 0 else "", E(s))
        for i, s in enumerate(ex["specs"]))
    variants = "\n".join("<li>%s</li>" % E(v) for v in ex["variants"])
    steps = "\n".join("<li>%s</li>" % E(s) for s in ex["steps"])
    cues = "\n".join("<li>%s</li>" % E(c) for c in ex["cues"])
    mistakes = "\n".join("<li>%s</li>" % E(m) for m in ex["mistakes"])
    return """
<section id="{code}">
  <div class="sec-h">
    <span class="sec-n" style="color:{fg};background:{bg};border-color:{fg}33">{code}</span>
    <div>
      <h2>{title} <span class="en">{en}</span></h2>
      <p class="role">{role}</p>
    </div>
  </div>
  <div class="specs">{specs}</div>

  <div class="figgrid">
{figs}
  </div>

  <div class="card">
    <h3>کدام نسخه را انتخاب کنم؟</h3>
    <ul class="clean">{variants}</ul>
  </div>

  <div class="card">
    <h3>مراحل اجرا — به همین ترتیب</h3>
    <ol class="steps">{steps}</ol>
  </div>

  <div class="two">
    <div class="card">
      <h3>نکات کلیدی</h3>
      <ul class="clean do">{cues}</ul>
    </div>
    <div class="card" style="border-color:#4d2229">
      <h3>اشتباهات رایج</h3>
      <ul class="clean dont">{mistakes}</ul>
    </div>
  </div>

  <div class="callout amber">
    <h3>خودآزمایی بعد از ست</h3>
    <p>{check}</p>
  </div>
</section>""".format(code=E(ex["code"]), title=E(ex["title"]), en=E(ex["en"]),
                     role=E(ex["role"]), specs=specs, figs=figs, variants=variants,
                     steps=steps, cues=cues, mistakes=mistakes, check=E(ex["check"]),
                     fg=fg, bg=bg)


def build():
    body = "\n".join(render_exercise(ex) for ex in EXERCISES)
    toc = "\n".join('<li><a href="#%s">%s — %s</a></li>' % (E(e["code"]), E(e["code"]), E(e["title"]))
                    for e in EXERCISES)
    page = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>راهنمای تصویری A5، A6 و A7 | برنامه سرشانه</title>
<meta name="description" content="آموزش تصویری نحوه اجرای نشر خم پشت شانه، نشر Y و چرخش خارجی کابل — با شکل، مراحل اجرا و اشتباهات رایج.">
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <span class="kicker"><span class="dot"></span> راهنمای تصویری سه حرکت پایانی جلسه سرشانه</span>
  <h1>نحوه اجرای A5، A6 و A7 — قدم‌به‌قدم با شکل</h1>
  <p class="sub">سه حرکت آخر برنامه، همان‌هایی هستند که پشت شانه را می‌سازند و شانه را سالم نگه می‌دارند.
  اینجا با شکل، مسیر حرکت، نقاط کلیدی بدن و اشتباهات رایج هر کدام را می‌بینی.</p>
  <div class="chips">
    <span class="chip">شکل‌ها: <b>وضعیت بدن + مسیر حرکت</b></span>
    <span class="chip">A5: <b>نشر خم</b></span>
    <span class="chip">A6: <b>نشر Y</b></span>
    <span class="chip">A7: <b>چرخش خارجی کابل</b></span>
  </div>
</header>

<nav class="toc"><ul>
  <li><a href="index.html">◂ بازگشت به برنامه کامل</a></li>
  {toc}
</ul></nav>

<div class="toolbar">
  <button type="button" onclick="window.print()">چاپ / ذخیره PDF این صفحه</button>
  <a href="shoulder-program.pdf" style="text-decoration:none"><button type="button">PDF کامل برنامه</button></a>
  <a href="poster-a5-a6-a7.png" style="text-decoration:none"><button type="button">پوستر تصویری (یک تصویر)</button></a>
</div>

{body}

<footer>
  <p><b style="color:var(--dim)">یادآوری قوانین مشترک این سه حرکت:</b>
  تمپو ۱ ثانیه بالا · ۱ ثانیه توقف اوج · ۲ تا ۳ ثانیه پایین · دامنه کامل تا مرز بدون درد ·
  آرنج در تمام ست با زاویه ثابت · وزنه‌ای که تکنیک را در تکرار آخر خراب نکند.</p>
  <p>در صورت وجود درد، سابقه دررفتگی، پارگی یا جراحی شانه، پیش از اجرا با پزشک ورزشی یا فیزیوتراپیست مشورت کن.
  شکل‌ها شماتیک هستند و برای انتقال «مسیر حرکت» طراحی شده‌اند، نه نمایش دقیق آناتومیک.</p>
</footer>
</div>
</body>
</html>
""".format(css=CSS, body=body, toc=toc)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("ساخته شد:", OUT, "(%d بایت)" % len(page))


if __name__ == "__main__":
    build()

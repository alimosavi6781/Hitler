#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پوستر تصویری یک‌صفحه‌ای برای حرکات A5، A6 و A7.

خروجی:
    poster-a5-a6-a7.pdf   (یک صفحه بلند)
    poster-a5-a6-a7.png   (همان صفحه به‌صورت تصویر، برای اشتراک‌گذاری)

هر حرکت: سرتیتر + دو شکل (وضعیت بدن و مسیر حرکت) + مراحل کوتاه اجرا +
نکته کلیدی و پرتکرارترین اشتباه.
"""
import os

import pymupdf
from PIL import Image

from build_pdf import (Program, R, AMBER, AMBER_BG, TEAL, TEAL_BG, ROSE, ROSE_BG,
                       BLUE, BLUE_BG, OK, DIM, DIM2, INK, LINE, BG)
from figures import FIGURES
from content_a567 import EXERCISES

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "poster-a5-a6-a7.pdf")
PNG = os.path.join(HERE, "poster-a5-a6-a7.png")

ACCENT = {"AMBER": (AMBER, AMBER_BG), "TEAL": (TEAL, TEAL_BG)}

# مراحل کوتاه مخصوص پوستر (نسخه مفصل در exercises-a5-a6-a7.html و PDF است)
SHORT = {
    "A5": [
        "ارتفاع دستگیره را هم‌سطح شانه تنظیم کن.",
        "سینه کامل روی پد، پیشانی روی لبه بالای پد.",
        "گریپ خنثی؛ آرنج ۱۰ تا ۲۰ درجه خم و ثابت.",
        "آرنج‌ها را به بیرون باز کن، نه با فشار کف دست.",
        "اوج: ۱ ثانیه توقف · برگشت: ۲ تا ۳ ثانیه.",
    ],
    "A6": [
        "میز شیب‌دار ۳۰ تا ۴۵ درجه، سینه و شکم کامل روی میز.",
        "دست‌ها آویزان با گریپ خنثی، شست رو به بالا.",
        "تیغه‌های شانه را به عقب و پایین ببر.",
        "در مسیر ۴۵ درجه بالا و جلو ببر تا شکل Y ساخته شود.",
        "دو ثانیه بالا، ۱ ثانیه توقف، ۱ تا ۲ ثانیه پایین.",
    ],
    "A7": [
        "پهلو به دستگاه؛ قرقره هم‌ارتفاع آرنج.",
        "حوله کوچک بین آرنج و پهلو (تا آخر ست بماند).",
        "آرنج ۹۰ درجه، مچ صاف و بدون چرخش.",
        "ساعد را از رو به شکم، به بیرون بچرخان.",
        "۱ ثانیه نگه دار و ۲ تا ۳ ثانیه برگردان.",
    ],
}
def fa_num(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


KEY = {
    "A5": ("نکته کلیدی", "حرکت از باز شدن آرنج‌ها می‌آید؛ اگر گردن یا ساعد می‌سوزد، آرنج‌ها را باز نکرده‌ای."),
    "A6": ("نکته کلیدی", "در نقطه اوج باید شست‌ها بالاتر از شانه و کمی جلوتر از سر باشند؛ مسیر «بالا و جلو»، نه کامل به طرفین."),
    "A7": ("نکته کلیدی", "دو خطای اصلی: جدا شدن آرنج از پهلو و تاب دادن تنه؛ با حوله و نگاه به آینه کنترل کن."),
}
RISK = {
    "A5": ("پرتکرارترین اشتباه", "بالا کشیدن شانه‌ها در نقطه اوج که حرکت را به شراگ تبدیل می‌کند."),
    "A6": ("پرتکرارترین اشتباه", "وزنه سنگین که بلافاصله حرکت را به شراگ و بالا‌تراپز منتقل می‌کند."),
    "A7": ("پرتکرارترین اشتباه", "وزنه سنگین و از دست دادن کنترل؛ این حرکت با وزنه سبک هم نتیجه می‌دهد."),
}


def draw_exercise(pdf, ex):
    """یک بلوک کامل (سرتیتر + دو شکل + مراحل + نکته و اشتباه) را رسم می‌کند."""
    if True:
        accent, accent_bg = ACCENT[ex["accent"]]

    # ----- سرتیتر حرکت
    y = pdf.get_y()
    pdf.set_fill_color(*accent_bg)
    pdf.rect(pdf.l_margin, y, pdf.cw, 15.0, style="F", round_corners=True, corner_radius=2.4)
    pdf.set_fill_color(*accent)
    pdf.rect(pdf.l_margin + pdf.cw - 1.8, y + 1.8, 1.6, 11.4, style="F",
             round_corners=True, corner_radius=0.7)
    pdf.set_font("vzb", "", 15.0)
    pdf.set_text_color(*INK)
    pdf.set_xy(pdf.l_margin + 4, y + 1.4)
    pdf.cell(pdf.cw - 30, 7.2, R("%s — %s" % (ex["code"], ex["title"])), align="R")
    pdf.set_font("vz", "", 9.6)
    pdf.set_text_color(*DIM)
    pdf.set_xy(pdf.l_margin + 4, y + 8.4)
    pdf.cell(pdf.cw - 42, 5.4, R(ex["en"]), align="R")
    pdf.set_font("vzb", "", 13.0)
    pdf.set_text_color(*accent)
    pdf.set_xy(pdf.l_margin + pdf.cw - 22, y + 4.4)
    pdf.cell(16, 6.0, ex["code"], align="C")
    pdf.set_y(y + 18.0)

    # ----- مشخصات
    pdf.chip_row([(s_, DIM, (240, 243, 248)) for s_ in ex["specs"]], gap_below=2.0)

    # ----- شکل‌ها
    pairs = [(FIGURES[key](), cap) for key, cap in ex["figures"]]
    pdf.fig_row(pairs, gap=5.0)

    # ----- مراحل کوتاه (دو ستونی)
    items = SHORT[ex["code"]]
    half = (len(items) + 1) // 2
    cols = [items[:half], items[half:]]
    start_no = [1, half + 1]
    w = (pdf.cw - 5.0) / 2
    h = 0.0
    for col in cols:
        hh = 0.0
        for it in col:
            pdf.set_font("vz", "", 10.2)
            hh += pdf.multi_cell(w - 10.0, 5.4, R(it), align="R", dry_run=True,
                                 output="HEIGHT") + 2.0
        h = max(h, hh)
    y = pdf.get_y()
    x = pdf.l_margin + pdf.cw - w
    for ci, col in enumerate(cols):
        yy = y
        for j, it in enumerate(col):
            n = start_no[ci] + j
            pdf.set_fill_color(*accent)
            pdf.rect(x + w - 7.0, yy + 0.3, 6.4, 6.4, style="F", round_corners=True,
                     corner_radius=1.6)
            pdf.set_font("vzb", "", 10.6)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(x + w - 7.0, yy + 1.2)
            pdf.cell(6.4, 4.6, R(fa_num(n)), align="C")
            pdf.set_font("vz", "", 10.2)
            pdf.set_text_color(*INK)
            pdf.set_xy(x, yy)
            pdf.multi_cell(w - 10.0, 5.4, R(it), align="R", new_x="LMARGIN", new_y="NEXT")
            yy = pdf.get_y() + 2.0
        x -= (w + 5.0)
    pdf.set_y(y + h + 1.0)

    # ----- نکته و اشتباه
    t1, c1 = KEY[ex["code"]]
    t2, c2 = RISK[ex["code"]]
    pdf.two_col([
        (t1, [c1], accent, OK),
        (t2, [c2], ROSE, ROSE),
    ], size=9.8, lh=5.0)


def _render_png(pdf_path, png_path, zoom=2.6):
    doc = pymupdf.open(pdf_path)
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    import numpy as np
    arr = np.asarray(img.convert("L"))
    rows = np.where(arr.min(axis=1) < 245)[0]
    bottom = int(rows[-1]) + 40 if len(rows) else img.height
    img = img.crop((0, 0, img.width, min(bottom, img.height)))
    img.save(png_path, optimize=True)
    return img.size


def build():
    pdf = Program(fmt=(210, 700))
    pdf.add_page()
    pdf.title_band("نحوه اجرای A5، A6 و A7 — راهنمای تصویری",
                   "نشر خم پشت شانه · نشر Y · چرخش خارجی کابل  |  "
                   "تمپو: ۱ ثانیه بالا، ۱ ثانیه توقف اوج، ۲ تا ۳ ثانیه پایین")
    pdf.ln(2)
    for k, ex in enumerate(EXERCISES):
        if k:
            pdf.need(240)
            y = pdf.get_y() + 1
            pdf.set_draw_color(*LINE)
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, y, pdf.l_margin + pdf.cw, y)
            pdf.set_y(y + 5)
        draw_exercise(pdf, ex)
    FOOTER = [
        ("قوانین مشترک این سه حرکت",
         "آرنج در تمام ست با زاویه ثابت · دامنه کامل تا مرز بدون درد · توقف یک‌ثانیه‌ای در اوج · "
         "وزنه‌ای که تکنیک را در تکرار آخر خراب نکند · در صورت درد تیز، ست را همان‌جا تمام کن.",
         TEAL_BG, TEAL),
        ("هشدار",
         "شکل‌ها شماتیک‌اند و برای انتقال وضعیت بدن و مسیر حرکت طراحی شده‌اند؛ جایگزین آموزش حضوری نیستند. "
         "در صورت سابقه آسیب یا جراحی شانه، پیش از اجرا با پزشک ورزشی یا فیزیوتراپیست مشورت کن.",
         ROSE_BG, ROSE),
    ]
    for title, body, bg, accent in FOOTER:
        pdf.box([body], bg=bg, accent=accent, title=title)
    pdf.output(PDF)
    print("ساخته شد:", PDF)
    print("ساخته شد:", PNG, _render_png(PDF, PNG))


def build_singles():
    """یک تصویر جدا برای هر حرکت — مناسب فرستادن در پیام‌رسان‌ها."""
    for ex in EXERCISES:
        path_pdf = os.path.join(HERE, "poster-%s.pdf" % ex["code"].lower())
        path_png = os.path.join(HERE, "poster-%s.png" % ex["code"].lower())
        pdf = Program(fmt=(210, 268))
        pdf.add_page()
        pdf.title_band("نحوه اجرای %s — %s" % (ex["code"], ex["title"]),
                       "%s  |  تمپو: ۱ ثانیه بالا، ۱ ثانیه توقف اوج، ۲ تا ۳ ثانیه پایین" % ex["en"])
        pdf.ln(2)
        draw_exercise(pdf, ex)
        pdf.output(path_pdf)
        size = _render_png(path_pdf, path_png, zoom=2.8)
        print("ساخته شد:", path_png, size)


if __name__ == "__main__":
    build()
    build_singles()

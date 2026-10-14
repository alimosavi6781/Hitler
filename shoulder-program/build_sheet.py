#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
برگه تصویری افقی A5/A6/A7

خروجی:
    figures-sheet-a5-a6-a7.png
    figures-sheet-a5-a6-a7.jpg   (سبک‌تر، برای ارسال در پیام‌رسان‌ها)

شش شکل در یک شبکه ۳×۱ ستونی و ۲ ردیفی با زیرنویس فارسی، در ابعاد معمول و افقی.
"""
import os

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display

from build_pdf import Program, R
from figures import FIGURES

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "ttf", "Vazirmatn-SemiBold.ttf")
FONT_B = os.path.join(HERE, "fonts", "ttf", "Vazirmatn-Bold.ttf")
PNG = os.path.join(HERE, "figures-sheet-a5-a6-a7.png")
JPG = os.path.join(HERE, "figures-sheet-a5-a6-a7.jpg")

_rs = ArabicReshaper(configuration={"delete_harakat": False, "support_ligatures": True})
fa = lambda s: get_display(_rs.reshape(s))

CELL_W = 780          # عرض هر خانه به پیکسل
GAP = 26
MARGIN = 30
HEADER = 126
CAPTION_H = 46
SCALE = 3.2           # رزولوشن رندر شکل‌ها

ITEMS = [
    ("a5_setup",   "A5 — شکل ۱: تنظیم دستگاه و وضعیت بدن (نمای پهلو)"),
    ("a5_sweep",   "A5 — شکل ۲: مسیر حرکت دست‌ها (نمای از بالا)"),
    ("a6_setup",   "A6 — شکل ۱: وضعیت بدن روی میز شیب‌دار"),
    ("a6_shape",   "A6 — شکل ۲: مسیر ۴۵ درجه و شکل Y (روبه‌رو)"),
    ("a7_setup",   "A7 — شکل ۱: وضعیت ایستاده و زاویه آرنج"),
    ("a7_rotation", "A7 — شکل ۲: مسیر چرخش ساعد (نمای از بالا)"),
]
TITLE = "نحوه اجرای A5، A6 و A7 — شکل‌ها"
SUB = "نشر خم پشت شانه · نشر Y · چرخش خارجی کابل"


def render_fig(key, w_px):
    """شکل را به تصویر تبدیل می‌کند (از همان هندسه مشترک figures.py)."""
    fig = FIGURES[key]()
    scale_mm = 0.1  # مقیاس دلخواه؛ فقط نسبت مهم است
    pdf = Program(fmt=(fig.w * scale_mm, fig.h * scale_mm))
    pdf.set_margins(0, 0, 0)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    fig.draw_pdf(pdf, 0, 0, scale_mm, R)
    zoom = w_px / (fig.w * scale_mm / 25.4 * 72.0)
    doc_path = "/tmp/_fig.pdf"
    pdf.output(doc_path)
    doc = pymupdf.open(doc_path)
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def main():
    f_title = ImageFont.truetype(FONT_B, 56)
    f_sub = ImageFont.truetype(FONT, 30)
    f_cap = ImageFont.truetype(FONT, 30)

    imgs = []
    for key, cap in ITEMS:
        im = render_fig(key, CELL_W)
        imgs.append((im, cap))

    cell_h = max(im.height for im, _ in imgs) + CAPTION_H
    cols, rows = 3, 2
    W = MARGIN * 2 + cols * CELL_W + (cols - 1) * GAP
    H = MARGIN * 2 + HEADER + rows * cell_h + (rows - 1) * GAP
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)

    # سربرگ
    d.rectangle([0, 0, W, HEADER], fill=(17, 21, 28))
    d.text((W - MARGIN, 8), fa(TITLE), font=f_title, fill=(255, 255, 255), anchor="ra")
    d.text((W - MARGIN, 78), fa(SUB), font=f_sub, fill=(176, 188, 204), anchor="ra")

    y = MARGIN + HEADER
    for r in range(rows):
        x = MARGIN
        for c in range(cols):
            i = r * cols + c
            im, cap = imgs[i]
            sheet.paste(im, (x, y))
            d.text((x + CELL_W // 2, y + im.height + 6), fa(cap), font=f_cap,
                   fill=(60, 70, 85), anchor="ma")
            x += CELL_W + GAP
        y += cell_h + GAP

    sheet.save(PNG, optimize=True)
    sheet.convert("RGB").save(JPG, quality=88, optimize=True, progressive=True)
    print("ساخته شد:", PNG, sheet.size, round(os.path.getsize(PNG) / 1024, 1), "KB")
    print("ساخته شد:", JPG, round(os.path.getsize(JPG) / 1024, 1), "KB")


if __name__ == "__main__":
    main()

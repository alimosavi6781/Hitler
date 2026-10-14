#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سازنده‌ی PDF «برنامه حرفه‌ای رشد سرشانه».

خروجی: shoulder-program.pdf  (در همین پوشه)

نیازمندی‌ها:
    pip install fpdf2 arabic-reshaper python-bidi

فونت: Vazirmatn (نسخه کامل) در پوشه‌ی fonts/ttf
راست‌به‌چپ: متن با arabic-reshaper (اتصال حروف) و python-bidi (ترتیب بصری)
           آماده و سپس به‌صورت LTR راست‌چین رندر می‌شود.
"""
import os

from fpdf import FPDF
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display

from figures import FIGURES
from content_a567 import EXERCISES

HERE = os.path.dirname(os.path.abspath(__file__))
FDIR = os.path.join(HERE, "fonts", "ttf")
OUT = os.path.join(HERE, "shoulder-program.pdf")

_rs = ArabicReshaper(configuration={
    "delete_harakat": False,
    "support_ligatures": True,
    "RIAL SIGN": False,
})


def R(s: str) -> str:
    """متن فارسی را برای نمایش راست‌به‌چپ آماده می‌کند."""
    return get_display(_rs.reshape(s))


# ---------------------------------------------------------------- palette
INK = (17, 21, 28)
DIM = (86, 96, 112)
DIM2 = (128, 138, 154)
AMBER = (176, 112, 16)
AMBER_BG = (253, 244, 227)
TEAL = (12, 108, 93)
TEAL_BG = (232, 246, 243)
ROSE = (166, 50, 50)
ROSE_BG = (253, 238, 238)
BLUE = (26, 92, 164)
BLUE_BG = (233, 241, 251)
OK = (24, 118, 66)
LINE = (210, 217, 227)
LINE2 = (231, 236, 243)
BG = (246, 248, 252)
WHITE = (255, 255, 255)


class Program(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.set_margins(14, 13, 14)
        self.set_auto_page_break(True, margin=15)
        self.add_font("vz", "", os.path.join(FDIR, "Vazirmatn-Regular.ttf"))
        self.add_font("vzb", "", os.path.join(FDIR, "Vazirmatn-Bold.ttf"))
        self.add_font("vzm", "", os.path.join(FDIR, "Vazirmatn-SemiBold.ttf"))
        self.set_font("vz", "", 9.6)
        self.alias_nb_pages()

    # ---------------------------------------------------------- plumbing
    @property
    def cw(self):
        return self.epw

    def need(self, h):
        if self.get_y() + h > self.h - self.b_margin:
            self.add_page()
            return True
        return False

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-11)
        self.set_draw_color(*LINE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.h - 11.5, self.w - self.r_margin, self.h - 11.5)
        self.set_font("vz", "", 7.4)
        self.set_text_color(*DIM2)
        self.set_x(self.l_margin)
        self.cell(self.epw, 4, R("برنامه حرفه‌ای رشد سرشانه — دلتوئید سه‌بخشی"), align="R")
        self.set_xy(self.l_margin, self.h - 11.6)
        self.cell(self.epw, 4, R("صفحه %d از {nb}" % self.page_no()), align="L")

    # ------------------------------------------------------------- atoms
    def title_band(self, title, sub):
        y = self.get_y()
        h = 26
        self.set_fill_color(*INK)
        self.rect(self.l_margin, y, self.cw, h, style="F", round_corners=True, corner_radius=2.5)
        self.set_font("vzb", "", 17)
        self.set_text_color(*WHITE)
        self.set_xy(self.l_margin + 5, y + 5.2)
        self.cell(self.cw - 10, 8, R(title), align="R")
        self.set_font("vz", "", 9.6)
        self.set_text_color(178, 188, 204)
        self.set_xy(self.l_margin + 5, y + 14.6)
        self.cell(self.cw - 10, 6, R(sub), align="R")
        self.set_y(y + h + 4)

    def h2(self, num, text, accent=AMBER):
        self.need(12)
        y = self.get_y() + 1.5
        self.set_fill_color(*accent)
        self.rect(self.l_margin + self.cw - 1.6, y + 0.4, 1.6, 5.6, style="F", round_corners=True,
                  corner_radius=0.7)
        self.set_font("vzb", "", 11.6)
        self.set_text_color(*INK)
        self.set_xy(self.l_margin, y)
        self.cell(self.cw - 5, 6.4, R("%s. %s" % (num, text)), align="R")
        self.set_y(y + 8.6)

    def p(self, text, size=9.5, color=DIM, lh=5.0, indent=0.0, gap=1.4, family="vz", style=""):
        self.set_font(family, style, size)
        self.set_text_color(*color)
        x = self.l_margin + indent
        w = self.cw - indent
        self.set_x(x)
        self.multi_cell(w, lh, R(text), align="R", new_x="LMARGIN", new_y="NEXT")
        if gap:
            self.ln(gap)

    def bullets(self, items, size=9.4, color=DIM, lh=4.9, indent=0.0, gap=1.1, marker=TEAL,
                family="vz"):
        for it in items:
            self.set_font(family, "", size)
            tw = self.cw - indent - 5.6
            self.set_font("vz", "", size)
            h = self.multi_cell(tw, lh, R(it), align="R", dry_run=True, output="HEIGHT")
            self.need(h + gap)
            y0 = self.get_y()
            self.set_fill_color(*marker)
            self.rect(self.l_margin + self.cw - 3.2, y0 + 1.6, 2.0, 2.0, style="F",
                      round_corners=True, corner_radius=0.6)
            self.set_text_color(*color)
            self.set_xy(self.l_margin + indent, y0)
            self.multi_cell(tw, lh, R(it), align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(gap)

    def chip(self, x_right, y, text, fg, bg, size=8.0, h=5.4, pad=2.4):
        self.set_font("vzm", "", size)
        w = self.get_string_width(R(text)) + 2 * pad
        x = x_right - w
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=1.6)
        self.set_text_color(*fg)
        self.set_xy(x, y + 0.55)
        self.cell(w, h - 1.1, R(text), align="C")
        return x - 2.0

    def chip_row(self, items, y=None, h=5.4, gap_below=2.6):
        # items: (text, fg, bg)
        y = self.get_y() if y is None else y
        self.need(h + gap_below)
        x_right = self.l_margin + self.cw
        for text, fg, bg in items:
            x_right = self.chip(x_right, y, text, fg, bg, h=h)
        self.set_y(y + h + gap_below)

    def box(self, lines, bg=BG, accent=AMBER, size=9.3, title=None, title_color=None):
        """کادر یادداشت با نوار رنگی سمت راست."""
        pad = 3.4
        tw = self.cw - 2 * pad - 2.6
        inner = []
        for ln in lines:
            self.set_font("vz", "", size)
            inner.append((ln, self.multi_cell(tw, 4.9, R(ln), align="R", dry_run=True,
                                              output="HEIGHT")))
        th = 0.0
        if title:
            self.set_font("vzb", "", size + 0.7)
            th = self.multi_cell(tw, 5.4, R(title), align="R", dry_run=True, output="HEIGHT") + 1.2
        h = pad * 2 + th + sum(hh + 1.1 for _, hh in inner) - 1.1
        self.need(h + 2)
        y = self.get_y()
        self.set_fill_color(*bg)
        self.rect(self.l_margin, y, self.cw, h, style="F", round_corners=True, corner_radius=2)
        self.set_fill_color(*accent)
        self.rect(self.l_margin + self.cw - 2.0, y + 1.6, 1.6, h - 3.2, style="F",
                  round_corners=True, corner_radius=0.6)
        yy = y + pad
        if title:
            self.set_font("vzb", "", size + 0.7)
            self.set_text_color(*(title_color or accent))
            self.set_xy(self.l_margin + pad, yy)
            self.multi_cell(tw, 5.4, R(title), align="R", new_x="LMARGIN", new_y="NEXT")
            yy = self.get_y() + 1.2
        for (ln, hh) in inner:
            self.set_font("vz", "", size)
            self.set_text_color(*INK)
            self.set_xy(self.l_margin + pad, yy)
            self.multi_cell(tw, 4.9, R(ln), align="R", new_x="LMARGIN", new_y="NEXT")
            yy = self.get_y() + 1.1
        self.set_y(y + h + 3.2)

    def table(self, headers, rows, widths, aligns=None, size=8.7, rh=6.0, zebra=True,
              head_bg=BG, head_fg=DIM):
        aligns = aligns or ["R"] * len(headers)
        ws = [self.cw * f for f in widths]
        self.need(rh * (len(rows) + 1) + 3)

        def row(cells, y, bold=False, fill=None, h=rh, head=False):
            if fill:
                self.set_fill_color(*fill)
                self.rect(self.l_margin, y, self.cw, h, style="F")
            x = self.l_margin + self.cw
            for i, c in enumerate(cells):
                w = ws[i]
                x -= w
                self.set_xy(x, y)
                if head:
                    self.set_font("vzm", "", size - 0.3)
                    self.set_text_color(*head_fg)
                elif bold:
                    self.set_font("vzb", "", size)
                    self.set_text_color(*INK)
                else:
                    self.set_font("vz", "", size)
                    self.set_text_color(*INK)
                self.cell(w, h, R(c), align=aligns[i])
            self.set_draw_color(*LINE2)
            self.set_line_width(0.18)
            self.line(self.l_margin, y + h, self.l_margin + self.cw, y + h)

        # موقعیت را دستی مدیریت می‌کنیم؛ متدهای رسم، مکان‌نما را جابه‌جا می‌کنند.
        y = self.get_y()

        def ensure(h):
            nonlocal y
            if y + h > self.h - self.b_margin:
                self.add_page()
                y = self.get_y()

        ensure(rh)
        row(headers, y, fill=head_bg, head=True)
        y += rh
        for i, r in enumerate(rows):
            ensure(rh)
            fill = WHITE if (not zebra or i % 2 == 0) else (249, 250, 253)
            row(r, y, fill=fill)
            y += rh
        self.set_y(y + 2.4)

    def card_row(self, cards, gap=4.0, size=9.0):
        """cards: list of (title, [(text, color)], accent) — در یک ردیف افقی."""
        n = len(cards)
        w = (self.cw - gap * (n - 1)) / n
        pad = 3.2
        tw = w - 2 * pad
        heights = []
        for title, lines, accent in cards:
            hh = 0.0
            if title:
                self.set_font("vzb", "", size + 0.6)
                hh += self.multi_cell(tw, 5.2, R(title), align="R", dry_run=True, output="HEIGHT") + 1.4
            for text, col in lines:
                self.set_font("vz", "", size - 0.4)
                hh += self.multi_cell(tw, 4.7, R(text), align="R", dry_run=True,
                                      output="HEIGHT") + 1.0
            heights.append(hh + 2 * pad - 1.0)
        h = max(heights)
        self.need(h + 3)
        y = self.get_y()
        x = self.l_margin + self.cw - w
        for (title, lines, accent), hh in zip(cards, heights):
            self.set_fill_color(250, 251, 254)
            self.set_draw_color(*LINE)
            self.set_line_width(0.2)
            self.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=1.8)
            self.set_fill_color(*accent)
            self.rect(x + w - 1.5, y + 1.5, 1.3, h - 3.0, style="F", round_corners=True,
                      corner_radius=0.5)
            yy = y + pad
            if title:
                self.set_font("vzb", "", size + 0.6)
                self.set_text_color(*INK)
                self.set_xy(x + pad, yy)
                self.multi_cell(tw, 5.2, R(title), align="R", new_x="LMARGIN", new_y="NEXT")
                yy = self.get_y() + 1.4
            for text, col in lines:
                self.set_font("vz", "", size - 0.4)
                self.set_text_color(*col)
                self.set_xy(x + pad, yy)
                self.multi_cell(tw, 4.7, R(text), align="R", new_x="LMARGIN", new_y="NEXT")
                yy = self.get_y() + 1.0
            x -= (w + gap)
        self.set_y(y + h + 3.4)


    # --------------------------------------------------- figures & lists
    def _lines_h(self, text, w, size, lh):
        self.set_font("vz", "", size)
        return self.multi_cell(w, lh, R(text), align="R", dry_run=True, output="HEIGHT")

    def numbered(self, items, size=9.2, lh=4.8, indent=7.2, gap=1.5, accent=AMBER):
        for i, it in enumerate(items, 1):
            tw = self.cw - indent
            h = self._lines_h(it, tw, size, lh)
            self.need(h + gap)
            y0 = self.get_y()
            self.set_fill_color(*accent)
            self.rect(self.l_margin + self.cw - 5.6, y0 + 0.9, 4.6, 4.6, style="F",
                      round_corners=True, corner_radius=1.2)
            self.set_font("vzb", "", 8.2)
            self.set_text_color(*WHITE)
            self.set_xy(self.l_margin + self.cw - 5.6, y0 + 1.7)
            self.cell(4.6, 3.4, R(str(i)), align="C")
            self.set_font("vz", "", size)
            self.set_text_color(*DIM)
            self.set_xy(self.l_margin, y0)
            self.multi_cell(tw, lh, R(it), align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(gap)

    def two_col(self, cols, size=8.8, lh=4.6, gap=4.0, pad=3.2):
        """cols: [(title, items, accent, marker_color), ...] در حالت راست‌به‌چپ"""
        w = (self.cw - gap * (len(cols) - 1)) / len(cols)
        tw = w - 2 * pad
        heights = []
        for title, items, accent, marker in cols:
            hh = 0.0
            if title:
                self.set_font("vzb", "", size + 0.6)
                hh += self.multi_cell(tw, 5.2, R(title), align="R", dry_run=True,
                                      output="HEIGHT") + 1.6
            for it in items:
                hh += self._lines_h(it, tw - 4.6, size, lh) + 1.2
            heights.append(hh + 2 * pad - 1.2)
        h = max(heights)
        self.need(h + 3.6)
        y = self.get_y()
        x = self.l_margin + self.cw - w
        for (title, items, accent, marker), hh in zip(cols, heights):
            self.set_fill_color(250, 251, 254)
            self.set_draw_color(*LINE)
            self.set_line_width(0.2)
            self.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
            self.set_fill_color(*accent)
            self.rect(x + w - 1.5, y + 1.6, 1.3, h - 3.2, style="F", round_corners=True,
                      corner_radius=0.5)
            yy = y + pad
            if title:
                self.set_font("vzb", "", size + 0.6)
                self.set_text_color(*INK)
                self.set_xy(x + pad, yy)
                self.multi_cell(tw, 5.2, R(title), align="R", new_x="LMARGIN", new_y="NEXT")
                yy = self.get_y() + 1.6
            for it in items:
                hhh = self._lines_h(it, tw - 4.6, size, lh)
                self.set_fill_color(*marker)
                self.rect(x + w - pad - 3.2, yy + 1.5, 2.0, 2.0, style="F",
                          round_corners=True, corner_radius=0.6)
                self.set_font("vz", "", size)
                self.set_text_color(*DIM)
                self.set_xy(x + pad, yy)
                self.multi_cell(tw - 4.6, lh, R(it), align="R", new_x="LMARGIN", new_y="NEXT")
                yy = self.get_y() + 1.2
            x -= (w + gap)
        self.set_y(y + h + 3.6)

    def fig_row(self, pairs, gap=4.0, cap_size=8.0):
        """pairs: [(Fig, caption), ...] در یک ردیف افقی"""
        n = len(pairs)
        w = (self.cw - gap * (n - 1)) / n
        heights = [w * f.h / f.w for f, _ in pairs]
        cap_h = 4.6 if any(c for _, c in pairs) else 0.0
        self.need(max(heights) + cap_h + 8)
        y = self.get_y()
        x = self.l_margin + self.cw - w
        for (f, cap), fh in zip(pairs, heights):
            f.draw_pdf(self, x, y, w / f.w, R)
            if cap:
                self.set_font("vz", "", cap_size)
                self.set_text_color(*DIM2)
                self.set_xy(x, y + fh + 1.2)
                self.cell(w, 4, R(cap), align="C")
            x -= (w + gap)
        self.set_y(y + max(heights) + cap_h + 3.6)

def polar(cx, cy, r, deg):
    import math
    a = math.radians(deg)
    return (cx + r * math.cos(a), cy - r * math.sin(a))


def annulus(pdf, cx, cy, r1, r2, a0, a1, fill, steps=18):
    import math
    pts = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        pts.append(polar(cx, cy, r2, a))
    for i in range(steps + 1):
        a = a1 + (a0 - a1) * i / steps
        pts.append(polar(cx, cy, r1, a))
    pdf.set_fill_color(*fill)
    pdf.polygon(pts, style="F")


# ============================================================== content
W = 0.62   # weight of first table column, helper for readability


def build():
    pdf = Program()
    pdf.add_page()

    # ---------------------------------------------------- page 1
    pdf.title_band(
        "برنامه حرفه‌ای رشد سرشانه",
        "دلتوئید سه‌بخشی · بلوک ۸ هفته‌ای · سطح متوسط · باشگاه کامل · RIR ۱ تا ۲")
    pdf.chip_row([
        ("۱ روز اختصاصی + دوز دوم", AMBER, AMBER_BG),
        ("حدود ۲۶ ست مستقیم در هفته", TEAL, TEAL_BG),
        ("۵۰ تا ۶۰ دقیقه", BLUE, BLUE_BG),
        ("دیلود در هفته ۴ و ۸", ROSE, ROSE_BG),
    ])
    pdf.ln(1.0)

    pdf.h2("۱", "اصولی که موتور رشد شانه‌اند")
    pdf.p("اگر سرشانه با وجود تمرین زیاد رشد نمی‌کند، تقریباً همیشه یکی از این شش مورد خراب است، نه ژن.")
    pdf.card_row([
        ("بخش میانی، ماشین عرض شانه", [
            ("چیزی که شانه را گرد و پهن نشان می‌دهد بخش جانبی است.", DIM),
            ("این بخش فقط با ابداکشن، یعنی نشر از پهلو، مستقیم بار می‌گیرد.", DIM),
        ], AMBER),
        ("بخش خلفی، نقطه کور", [
            ("بیشتر افراد آن را نادیده می‌گیرند و شانه جلو افتاده می‌شود.", DIM),
            ("در این برنامه حجم پشت شانه کمتر از جلوی شانه نیست.", DIM),
        ], TEAL),
        ("بخش قدامی، تقریباً مفت", [
            ("هر پرس سینه و سرشانه جلوی دلتوئید را پر می‌کند.", DIM),
            ("پس فقط یک حرکت پرس سنگین کافی است.", DIM),
        ], BLUE),
    ])
    pdf.card_row([
        ("ست مؤثر، پنج تکرار آخر", [
            ("محرک رشد، تکرارهای نزدیک به ناتوانی است.", DIM),
            ("هدف: RIR یک تا دو و در آخرین ست هر حرکت RIR صفر تا یک.", DIM),
        ], AMBER),
        ("اضافه‌بار پیشرونده", [
            ("بدون پیشروی، بدن دلیلی برای ساختن عضله ندارد.", DIM),
            ("روش: اول تکرار را زیاد کن، بعد وزنه را ۲.۵ درصد.", DIM),
        ], TEAL),
        ("تنش در دامنه کشیده", [
            ("بارگذاری عضله در وضعیت کشیده محرک قوی‌تری است.", DIM),
            ("در نشر جانبی یعنی دست از عقب بدن شروع کند.", DIM),
        ], BLUE),
    ])

    pdf.h2("۲", "آناتومی: دقیقاً چه چیزی را بزرگ می‌کنیم؟")
    y0 = pdf.get_y()
    cx, cy = pdf.l_margin + pdf.cw - 34, y0 + 19
    # torso + arm schematics (top view, arm pointing left, RTL friendly)
    pdf.set_fill_color(*BG)
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.2)
    pdf.rect(pdf.l_margin + pdf.cw - 66, y0 + 3, 11, 32, style="DF", round_corners=True,
             corner_radius=2)
    pdf.rect(cx - 26, cy - 4.2, 26, 8.4, style="DF", round_corners=True, corner_radius=3)
    pdf.set_fill_color(232, 236, 244)
    pdf.circle(cx, cy, 6.6, style="F")
    annulus(pdf, cx, cy, 7.4, 11.6, 90, 30, (230, 120, 120))     # anterior (top)
    annulus(pdf, cx, cy, 7.4, 11.6, 30, -30, (226, 168, 60))     # lateral (outward/left)
    annulus(pdf, cx, cy, 7.4, 11.6, -30, -90, (95, 190, 172))    # posterior (bottom)
    pdf.set_font("vz", "", 7.4)
    pdf.set_text_color(*DIM2)
    pdf.set_xy(cx - 14, cy - 19.5)
    pdf.cell(28, 4, R("بخش قدامی"), align="C")
    pdf.set_xy(cx - 14, cy + 16.5)
    pdf.cell(28, 4, R("بخش خلفی"), align="C")
    pdf.set_xy(cx + 12.5, cy - 2)
    pdf.cell(24, 4, R("میانی"), align="R")
    pdf.set_xy(pdf.l_margin + pdf.cw - 66, y0 + 18)
    pdf.cell(11, 4, R("تنه"), align="C")

    tw = pdf.cw - 72
    x_keep, y_keep = pdf.get_x(), pdf.get_y()
    # table placed to the left of the drawing
    pdf.set_xy(pdf.l_margin, y0)
    x = pdf.l_margin
    headers = ["بخش", "وظیفه اصلی", "ست مستقیم در هفته"]
    rows = [
        ["میانی (جانبی)", "ابداکشن، عرض شانه و نمای V شکل", "۱۰ تا ۱۴"],
        ["خلفی (پشتی)", "اکستنشن و چرخش خارجی، تعادل و ضخامت", "۸ تا ۱۲"],
        ["قدامی (جلویی)", "فلکسن، بیشتر از پرس‌ها غیرمستقیم", "۰ تا ۴"],
    ]
    widths = [0.30, 0.48, 0.22]
    ws = [tw * f for f in widths]
    rh = 6.4
    yy = y0
    for i, r in enumerate([headers] + rows):
        xx = x + tw
        pdf.set_fill_color(*(BG if i == 0 else (WHITE if i % 2 else (250, 251, 254))))
        pdf.rect(x, yy, tw, rh, style="F")
        for j, c in enumerate(r):
            w = ws[j]
            xx -= w
            pdf.set_xy(xx, yy)
            if i == 0:
                pdf.set_font("vzm", "", 8.2)
                pdf.set_text_color(*DIM)
            else:
                pdf.set_font("vzb" if j == 0 else "vz", "", 8.4)
                pdf.set_text_color(*INK)
            pdf.cell(w, rh, R(c), align=("R" if j < 2 else "C"))
        pdf.set_draw_color(*LINE2)
        pdf.set_line_width(0.18)
        pdf.line(x, yy + rh, x + tw, yy + rh)
        yy += rh
    pdf.set_xy(x, yy + 2.5)
    pdf.p("پژوهش‌ها به‌طور کلی نشان می‌دهند تقسیم حجم یکسان روی ۲ جلسه نتایجی کمی بهتر از ۱ جلسه می‌دهد؛ "
          "به همین دلیل روز اختصاصی سرشانه با یک دوز دوم سبک همراه شده است.", size=8.8, gap=0)
    pdf.set_y(max(pdf.get_y(), y0 + 40))
    pdf.box(
        ["یا فقط همان یک روز اختصاصی را انجام بده و رشد بگیر؛ دوز دوم بازده را بالاتر و خستگی هر جلسه را کمتر می‌کند."],
        bg=AMBER_BG, accent=AMBER, title="نکته تناوب",
    )

    # ---------------------------------------------------- page 2
    pdf.add_page()
    pdf.h2("۳", "گرم‌کردن اختصاصی شانه، ۱۰ دقیقه، غیرقابل مذاکره")
    pdf.p("با سابقه تق‌تق و درد خفیف، این بخش بیشترین اثر را روی بدون درد ماندن و کیفیت جلسه دارد.")
    pdf.table(
        ["#", "حرکت", "حجم", "هدف"],
        [
            ["۱", "دوچرخه یا تردمیل سبک", "۳ تا ۵ دقیقه", "افزایش دمای عمومی بدن"],
            ["۲", "کشش کش از جلو (Band Pull-apart)", "۲ × ۲۰", "فعال‌سازی پشت شانه و بین‌کتفی"],
            ["۳", "چرخش خارجی با کش", "۲ × ۱۵ هر دست", "گرم‌کردن روتاتور کاف"],
            ["۴", "Y-T-W روی میز شیب‌دار", "۲ × ۱۰ هر حرف", "پایین‌تراپز و کنترل تیغه شانه"],
            ["۵", "اسلاید دیوار و کشش سراتوس", "۲ × ۱۰", "سراتوس و چرخش بالایی کتف"],
            ["۶", "دو ست سبک از حرکت اول", "۵۰٪ و ۷۰٪ وزنه کار", "آماده‌سازی اختصاصی پرس"],
        ],
        [0.05, 0.42, 0.22, 0.31],
        aligns=["C", "R", "C", "R"],
    )
    pdf.box(["گرم‌کردن باید خود حرکت را شبیه‌سازی کند، نه اینکه خسته‌ات کند. ست سبک را هرگز تا نزدیک ناتوانی نزن."],
            bg=TEAL_BG, accent=TEAL, title="قانون گرم‌کردن مؤثر")

    pdf.h2("۴", "جلسه اختصاصی سرشانه — Session A")
    pdf.p("ترتیب حرکات تصادفی نیست: از سنگین به سبک، از چندمفصلی به تک‌مفصلی و در انتها کار سلامت شانه. "
          "کل ست کاری: ۲۰ ست به‌همراه ۲ ست سلامت شانه.")

    def ex(code, title, specs, note, warn=None, accent=AMBER):
        pad = 3.4
        tw = pdf.cw - 2 * pad - 12
        pdf.set_font("vzb", "", 10.0)
        th = pdf.multi_cell(tw, 5.4, R(title), align="R", dry_run=True, output="HEIGHT")
        hh = 0.0
        for t in ([note] + ([warn] if warn else [])):
            pdf.set_font("vz", "", 8.8)
            hh += pdf.multi_cell(tw, 4.7, R(t), align="R", dry_run=True, output="HEIGHT") + 1.2
        h = pad * 2 + th + 1.6 + 5.6 + hh - 0.4
        pdf.need(h + 3)
        y = pdf.get_y()
        pdf.set_fill_color(250, 251, 254)
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(0.2)
        pdf.rect(pdf.l_margin, y, pdf.cw, h, style="DF", round_corners=True, corner_radius=2)
        pdf.set_fill_color(*accent)
        pdf.rect(pdf.l_margin + pdf.cw - 1.8, y + 1.8, 1.5, h - 3.6, style="F",
                  round_corners=True, corner_radius=0.7)
        # badge
        bx, by = pdf.l_margin + pdf.cw - pad - 8.4, y + pad
        pdf.set_fill_color(*accent)
        pdf.rect(bx, by, 8.4, 6.4, style="F", round_corners=True, corner_radius=1.8)
        pdf.set_font("vzb", "", 8.4)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(bx, by + 0.7)
        pdf.cell(8.4, 5.0, code, align="C")
        # title
        pdf.set_font("vzb", "", 10.0)
        pdf.set_text_color(*INK)
        pdf.set_xy(pdf.l_margin + pad, y + pad)
        pdf.multi_cell(tw, 5.4, R(title), align="R", new_x="LMARGIN", new_y="NEXT")
        yy = pdf.get_y() + 1.6
        # specs
        x_right = pdf.l_margin + pdf.cw - pad
        for i, s in enumerate(specs):
            fg, bg = (AMBER, AMBER_BG) if i == 0 else (DIM, (240, 243, 248))
            x_right = pdf.chip(x_right, yy, s, fg, bg, size=7.8, h=5.2)
        yy += 5.2 + 1.8
        # notes
        for t, col, sz in [(note, DIM, 8.8), (warn, ROSE, 8.6)]:
            if not t:
                continue
            pdf.set_font("vz", "", sz)
            pdf.set_text_color(*col)
            pdf.set_xy(pdf.l_margin + pad, yy)
            pdf.multi_cell(tw, 4.7, R(t), align="R", new_x="LMARGIN", new_y="NEXT")
            yy = pdf.get_y() + 1.2
        pdf.set_y(y + h + 2.8)

    ex("A1", "پرس سرشانه دمبل نشسته با پشتی ۸۰ تا ۸۵ درجه",
       ["۴ ست", "۶ تا ۱۰ تکرار", "RIR ۱ تا ۲", "استراحت ۲ تا ۳ دقیقه", "قدامی + میانی"],
       "پشتی را روی ۸۰ تا ۸۵ درجه بگذار؛ کاملاً صاف فشار شانه را زیاد می‌کند. دمبل را با گریپ خنثی یا ۴۵ درجه "
       "نگه دار و آرنج را حدود ۳۰ درجه جلوتر از تنه بیاور. پرس را در دامنه‌ای تمام کن که بدون درد است.",
       "جایگزین شانه‌دوست: پرس دستگاه با گریپ خنثی یا پرس لندماین که مسیرش برای شانه حساس مهربان‌تر است.")
    ex("A2", "نشر جانبی کابل تک‌دست از پشت بدن",
       ["۴ ست", "۱۲ تا ۱۸ تکرار", "RIR ۱", "استراحت ۶۰ تا ۹۰ ثانیه", "میانی"],
       "قرقره در پایین‌ترین حالت، دست مقابل کابل بایست و کابل را از پشت بدن عبور بده تا دست عقب‌تر از بدن شروع کند. "
       "آرنج ۱۰ تا ۲۰ درجه خم و ثابت، حرکت فقط از مفصل شانه، تنه بدون تاب. فاز منفی ۲ تا ۳ ثانیه.")
    ex("A3", "نشر جانبی دستگاه یا دمبل خم‌شده (Lean-away)",
       ["۳ ست", "۱۲ تا ۱۵ تکرار", "RIR ۰ تا ۱", "استراحت ۶۰ تا ۹۰ ثانیه", "میانی"],
       "ست آخر را با دراپ‌ست یا رست‌پاز تمام کن: وزنه را ۲۵ تا ۳۰ درصد کم کن و بدون استراحت ادامه بده. "
       "اگر بدون درد بود، چند تکرار پارشال در نیمه کشیده اضافه کن؛ این ناحیه محرک قوی‌تری برای بخش میانی است.")

    # ---------------------------------------------------- page 3
    pdf.add_page()
    ex("A4", "فیس‌پول با طناب روی کابل",
       ["۳ ست", "۱۵ تا ۲۰ تکرار", "RIR ۱ تا ۲", "استراحت ۶۰ ثانیه", "خلفی + پایین‌تراپز"],
       "قرقره در ارتفاع صورت. طناب را به سمت پیشانی بکش، آرنج بالاتر از مچ، و در انتها یک چرخش خارجی کوچک "
       "اضافه کن. تیغه‌های شانه را عقب و پایین ببر و شانه را بالا نکش. وزنه سبک و کیفیت بالا.")
    ex("A5", "نشر خم (پشت شانه) با دستگاه یا کابل",
       ["۳ ست", "۱۲ تا ۲۰ تکرار", "RIR ۱", "استراحت ۶۰ تا ۹۰ ثانیه", "خلفی"],
       "سینه و پیشانی روی پد، گردن در راستای بدن. آرنج کمی خم و ثابت. حرکت را با کشیدن آرنج انجام بده، "
       "نه با فشار کف دست. در نقطه اوج یک توقف یک‌ثانیه‌ای داشته باش.")
    ex("A6", "نشر Y روی میز شیب‌دار یا با کابل",
       ["۳ ست", "۱۲ تا ۱۵ تکرار", "RIR ۱", "استراحت ۶۰ ثانیه", "خلفی + پایین‌تراپز"],
       "شانه‌دوست‌ترین حرکت این برنامه: مسیر ۴۵ درجه بالای سر با گریپ خنثی، همان الگویی که برای تقویت کتف و "
       "روتاتور کاف استفاده می‌شود. از ۱ تا ۲ کیلو شروع کن؛ اینجا کیفیت کامل مهم است، نه وزنه.", accent=TEAL)
    ex("A7", "چرخش خارجی کابل (فینیشر سلامت شانه)",
       ["۲ ست", "۱۵ تکرار هر دست", "سبک، بدون ناتوانی", "استراحت ۴۵ تا ۶۰ ثانیه", "روتاتور کاف"],
       "آرنج ۹۰ درجه و چسبیده به پهلو، ساعد را به بیرون بچرخان و کنترل‌شده برگردان. این حرکت برای رشد دلتوئید "
       "نیست؛ برای این است که جلسه بعد هم بتوانی بدون درد پرس کنی.", accent=TEAL)
    pdf.box([
        "تمپو: ۱ ثانیه بالا، ۱ ثانیه توقف در اوج، ۲ تا ۳ ثانیه پایین.",
        "دامنه: کامل تا جایی که بدون درد ممکن است؛ نیمه‌کاره هیچ‌وقت.",
        "تنفس: دم در فاز منفی و بازدم در فاز مثبت.",
        "بین ست‌ها تایمر بگذار؛ کوتاه‌کردن خودسرانه استراحت وزنه را پایین می‌آورد و از حجم کم می‌کند."],
        bg=AMBER_BG, accent=AMBER, title="چطور ست را دقیق بزنم؟")

    # ---------------------------------------------------- page 4
    pdf.add_page()
    pdf.h2("۵", "دوز دوم هفتگی — کلید رشد سریع‌تر", accent=TEAL)
    pdf.p("این دو حرکت را در انتهای روز پرس یا پشت اضافه کن: ۴۸ تا ۷۲ ساعت بعد از جلسه اختصاصی.")
    pdf.table(
        ["حرکت", "ست × تکرار", "شدت", "کجا بچینی"],
        [
            ["نشر جانبی کابل تک‌دست یا دستگاه", "۳ × ۱۲ تا ۲۰", "RIR ۱", "انتهای روز پرس سینه"],
            ["نشر خم کابل", "۲ تا ۳ × ۱۵ تا ۲۰", "RIR ۱ تا ۲", "انتهای روز پرس یا روز پشت"],
        ],
        [0.40, 0.22, 0.14, 0.24],
        aligns=["R", "C", "C", "R"],
    )
    pdf.chip_row([
        ("۵ تا ۶ ست در دوز دوم", TEAL, TEAL_BG),
        ("۲ بار در هفته هر بخش", BLUE, BLUE_BG),
        ("فاصله ۴۸ تا ۷۲ ساعت", AMBER, AMBER_BG),
    ])

    pdf.h2("۶", "نقشه ۸ هفته‌ای پیشروی")
    pdf.table(
        ["هفته", "حجم", "شدت", "تمرکز جلسه"],
        [
            ["هفته ۱", "۹۰٪", "RIR ۳", "یادگیری تکنیک و ثبت وزنه پایه"],
            ["هفته ۲", "۱۰۰٪", "RIR ۲ تا ۳", "یک تکرار بیشتر در هر ست نسبت به هفته ۱"],
            ["هفته ۳", "۱۰۰٪", "RIR ۱ تا ۲", "سنگین‌ترین هفته بلوک اول، آخرین ست RIR صفر"],
            ["هفته ۴", "۵۰ تا ۶۰٪", "RIR ۴", "دیلود: وزنه را نگه دار، نصف ست‌ها"],
            ["هفته ۵", "۱۰۰٪ +", "RIR ۲ تا ۱", "شروع بلوک شدت: دراپ‌ست یا رست‌پاز در ست آخر"],
            ["هفته ۶", "۱۰۵٪", "RIR ۱", "اضافه‌کردن تکرار پارشال در حرکت A3"],
            ["هفته ۷", "۱۰۵ تا ۱۱۰٪", "RIR ۰ تا ۱", "هفته رکورد: عبور از وزنه هفته ۳"],
            ["هفته ۸", "۵۰٪", "RIR ۴ تا ۵", "دیلود، اندازه‌گیری و عکس، شروع بلوک بعد"],
        ],
        [0.14, 0.14, 0.14, 0.58],
        aligns=["C", "C", "C", "R"],
    )
    pdf.box([
        "گام ۱: در بازه تکرار بمان و هر جلسه یک تکرار اضافه کن تا به سقف بازه برسی.",
        "گام ۲: وقتی در همه ست‌ها به سقف رسیدی، وزنه را ۲.۵ درصد زیاد کن و تکرار را از کف بازه شروع کن.",
        "گام ۳: این چرخه را تکرار کن. معیار واقعی پیشرفت همین است، نه سوزش یا کوفتگی.",
        "اگر پیشروی متوقف شد: خواب و کالری را چک کن، یک هفته دیلود بزن، ترتیب حرکات را عوض کن تا حرکت ضعیف اول بیاید."],
        bg=AMBER_BG, accent=AMBER, title="قانون پیشروی دوگانه")

    # ---------------------------------------------------- page 5
    pdf.add_page()
    pdf.h2("۷", "شانه‌ای که تق‌تق می‌دهد — پروتکل مراقبت", accent=ROSE)
    pdf.p("تق‌تق بدون درد معمولاً بی‌خطر است و در بیشتر افراد هم وجود دارد. مسئله وقتی شروع می‌شود که تق‌تق "
          "همراه درد، ضعف یا محدودشدن دامنه باشد.")
    pdf.card_row([
        ("بکن", [
            ("گرم‌کردن کامل قبل از هر جلسه، بدون استثنا.", DIM),
            ("نسبت کشش به پرس در هفته حداقل یک به یک، بهتر دو به یک.", DIM),
            ("تقویت روتاتور کاف دو تا سه بار در هفته، سبک و پرتکرار.", DIM),
            ("تمرین در دامنه بدون درد و سخت‌کردن عضله در همان دامنه.", DIM),
            ("پرس با گریپ خنثی یا دمبل که مسیر آزادتری دارد.", DIM),
            ("تحرک قفسه سینه: فوم‌رول و کشش درگاه.", DIM),
            ("خواب به پشت یا پهلو با بالش کوتاه، دست زیر سر نگذار.", DIM),
        ], OK),
        ("نکن", [
            ("پرس از پشت گردن در هر شرایطی.", DIM),
            ("زیربغل سیم‌کش با گریپ بسته و آرنج بالاتر از شانه.", DIM),
            ("بالا بردن وزنه از سطح شانه همراه با درد.", DIM),
            ("دیپ و شنا با عمق بیش از حد.", DIM),
            ("اصرار روی پرس سنگین در روزی که درد داری.", DIM),
            ("بازکردن اجباری شانه برای صدا دادن.", DIM),
            ("تمرین روزانه سرشانه؛ این عضله به ۴۸ ساعت فاصله نیاز دارد.", DIM),
        ], ROSE),
    ])
    pdf.box([
        "درد شبانه یا دردی که خوابت را می‌برد؛ ضعف ناگهانی در بلند کردن دست؛ کاهش واضح دامنه حرکت؛ "
        "درد پس از یک ضربه یا کشیدگی ناگهانی. در این موارد تمرین را متوقف کن و ارزیابی تخصصی بگیر."],
        bg=ROSE_BG, accent=ROSE, title="کِی باید به فیزیوتراپیست یا پزشک مراجعه کنی؟")

    pdf.h2("۸", "تغذیه و ریکاوری")
    pdf.table(
        ["شاخص", "مقدار", "توضیح"],
        [
            ["مازاد کالری", "۱۰ تا ۱۵ درصد", "حدود ۲۵۰ تا ۴۰۰ کیلوکالری بالای نیاز روزانه"],
            ["پروتئین", "۱.۶ تا ۲.۲ گرم بر کیلوگرم", "در ۳ تا ۵ وعده تقسیم شود"],
            ["کراتین", "۳ تا ۵ گرم در روز", "مونوهیدرات، هر روز و ساعتش مهم نیست"],
            ["خواب", "۷ تا ۹ ساعت", "کمبود خواب مستقیماً سنتز پروتئین عضله را کم می‌کند"],
            ["آب", "۳۰ تا ۴۰ میلی‌لیتر بر کیلوگرم", "کم‌آبی عملکرد را در ست‌های آخر پایین می‌آورد"],
        ],
        [0.24, 0.30, 0.46],
        aligns=["R", "C", "R"],
    )
    pdf.box([
        "با تمرین منظم و پیشروی درست، ۱ تا ۲ سانتی‌متر اضافه‌شدن دور شانه در یک بلوک ۸ هفته‌ای واقع‌بینانه است، "
        "اما تغییر ظاهری مشهود عرض شانه معمولاً ۳ تا ۶ ماه زمان می‌برد. کسی که ۶ ماه با یک برنامه پیش برود، "
        "از کسی که ۶ برنامه را در ۶ ماه عوض کرده وضع بسیار بهتری دارد."],
        bg=BG, accent=BLUE, title="یک نکته صادقانه درباره انتظارها", title_color=BLUE)

    pdf.h2("۹", "سنجش پیشرفت، با عدد نه با حس", accent=TEAL)
    pdf.table(
        ["شاخص", "روش سنجش", "هر چند وقت"],
        [
            ["عرض شانه", "فاصله دو استخوان آکرومیون با متر پارچه‌ای، بازوها شل", "۴ هفته"],
            ["دور سینه", "ارتفاع نوک سینه، پایان بازدم، نوار افقی", "۴ هفته"],
            ["دور بازو", "نقطه اوج بازوی سفت‌شده، همیشه همان نقطه", "۴ هفته"],
            ["عکس پیشرفت", "نور و فاصله یکسان، رو‌به‌رو و پهلو و پشت، صبح ناشتا", "۴ هفته"],
            ["لاگ تمرین", "وزنه و تکرار و RIR هر ست، همان جدول صفحه آخر", "هر جلسه"],
        ],
        [0.20, 0.62, 0.18],
        aligns=["R", "R", "C"],
    )
    pdf.box(["کوفتگی عضلانی، سوزش حین ست و خستگی زیاد هیچ‌کدام ملاک رشد نیستند. تکرار بیشتر یا وزنه بیشتر با "
             "همان کیفیت تکنیک، تنها معیار درست است."],
            bg=BG, accent=ROSE, title="معیارهای غلط", title_color=ROSE)
    y = pdf.get_y() + 1
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pdf.cw, y)
    pdf.set_y(y + 2.5)
    pdf.p("منابع کلیدی: Schoenfeld و همکاران، J Sports Sci ۲۰۱۷ (حجم هفتگی و هایپرتروفی) · Refalo و همکاران، "
          "Sports Med ۲۰۲۳ (فاصله از ناتوانی) · Berton و همکاران، Front Sports Act Living ۲۰۲۲ (متاآنالیز چتر) · "
          "Schoenfeld و همکاران، J Sports Sci ۲۰۱۹ (تناوب هفتگی).", size=8.2, color=DIM2, lh=4.6, gap=2.5)
    pdf.p("هشدار: این سند یک راهنمای آموزشی برای فرد با سابقه تمرینی متوسط، دسترسی به باشگاه کامل و بدون آسیب حاد "
          "شانه است. در صورت وجود درد، سابقه دررفتگی، پارگی یا جراحی شانه، پیش از اجرا با پزشک ورزشی یا "
          "فیزیوتراپیست مشورت کن.", size=8.2, color=DIM2, lh=4.6, gap=0)

    # ------------------------------------------- appendix: illustrated A5-A7
    pdf.add_page()
    pdf.title_band("پیوست — راهنمای تصویری A5، A6 و A7",
                   "شکل‌ها شماتیک‌اند و برای انتقال «وضعیت بدن و مسیر حرکت» طراحی شده‌اند · "
                   "تمپو: ۱ ثانیه بالا، ۱ ثانیه توقف اوج، ۲ تا ۳ ثانیه پایین")
    pdf.ln(1.5)

    ACC = {"AMBER": (AMBER, AMBER_BG), "TEAL": (TEAL, TEAL_BG)}
    for k, ex in enumerate(EXERCISES):
        if k:
            pdf.add_page()
        accent, accent_bg = ACC[ex["accent"]]
        # سرتیتر حرکت
        pdf.need(20)
        y = pdf.get_y()
        pdf.set_fill_color(*accent_bg)
        pdf.rect(pdf.l_margin, y, pdf.cw, 13.6, style="F", round_corners=True,
                 corner_radius=2)
        pdf.set_fill_color(*accent)
        pdf.rect(pdf.l_margin + pdf.cw - 1.6, y + 1.6, 1.5, 10.4, style="F",
                 round_corners=True, corner_radius=0.6)
        pdf.set_font("vzb", "", 12.4)
        pdf.set_text_color(*INK)
        pdf.set_xy(pdf.l_margin + 3.4, y + 1.4)
        pdf.cell(pdf.cw - 22, 6.4, R("%s — %s" % (ex["code"], ex["title"])), align="R")
        pdf.set_font("vz", "", 8.4)
        pdf.set_text_color(*DIM)
        pdf.set_xy(pdf.l_margin + 3.4, y + 7.6)
        pdf.cell(pdf.cw - 22, 5.0, R(ex["role"]), align="R")
        pdf.set_font("vzm", "", 9.4)
        pdf.set_text_color(*accent)
        pdf.set_xy(pdf.l_margin + pdf.cw - 16, y + 4.2)
        pdf.cell(12, 5.0, ex["code"], align="C")
        pdf.set_y(y + 16.6)
        pdf.chip_row([(s_, DIM, (240, 243, 248)) for s_ in ex["specs"]])
        # شکل‌ها
        pairs = [(FIGURES[key](), cap) for key, cap in ex["figures"]]
        pdf.fig_row(pairs)
        # نسخه‌ها
        pdf.two_col([
            ("کدام نسخه را انتخاب کنم؟", ex["variants"], accent, accent),
            ("خودآزمایی بعد از ست", [ex["check"]], AMBER, OK),
        ])
        # مراحل اجرا
        pdf.set_font("vzb", "", 10.4)
        pdf.set_text_color(*INK)
        pdf.set_x(pdf.l_margin)
        pdf.cell(pdf.cw, 6, R("مراحل اجرا — به همین ترتیب"), align="R")
        pdf.ln(7.2)
        pdf.numbered(ex["steps"], accent=accent)
        # نکات و اشتباهات
        pdf.two_col([
            ("نکات کلیدی", ex["cues"], accent, OK),
            ("اشتباهات رایج", ex["mistakes"], ROSE, ROSE),
        ])
    pdf.add_page()
    pdf.box(["تمپو ۱ ثانیه بالا، ۱ ثانیه توقف اوج، ۲ تا ۳ ثانیه پایین · دامنه کامل تا مرز بدون درد · "
             "آرنج در تمام ست با زاویه ثابت · وزنه‌ای که تکنیک را در تکرار آخر خراب نکند."],
            bg=TEAL_BG, accent=TEAL, title="قوانین مشترک این سه حرکت")
    pdf.box(["اگر درد، سابقه دررفتگی، پارگی یا جراحی شانه داری، پیش از اجرا با پزشک ورزشی یا فیزیوتراپیست "
             "مشورت کن. شکل‌ها شماتیک‌اند و جایگزین آموزش حضوری نیستند."],
            bg=ROSE_BG, accent=ROSE, title="هشدار")
    pdf.set_y(pdf.get_y() + 1)

    # ---------------------------------------------------- page 6 : log card
    pdf.add_page()
    pdf.title_band("کارت جلسه سرشانه — قابل چاپ",
                   "این صفحه را جدا چاپ کن و در باشگاه همراه داشته باش · جلسه A")
    pdf.chip_row([
        ("۲۰ ست کاری + ۲ ست سلامت", AMBER, AMBER_BG),
        ("۵۰ تا ۶۰ دقیقه", BLUE, BLUE_BG),
        ("تاریخ: .................", TEAL, TEAL_BG),
    ])
    pdf.ln(1)
    pdf.table(
        ["#", "حرکت", "ست × تکرار", "شدت", "استراحت", "وزنه و تکرار هر ست (پر کن)"],
        [
            ["A1", "پرس سرشانه دمبل نشسته", "۴ × ۶ تا ۱۰", "RIR ۱–۲", "۲ تا ۳ دقیقه", "۱)        ۲)        ۳)        ۴)"],
            ["A2", "نشر جانبی کابل تک‌دست", "۴ × ۱۲ تا ۱۸", "RIR ۱", "۶۰ تا ۹۰ ثانیه", "۱)        ۲)        ۳)        ۴)"],
            ["A3", "نشر جانبی دستگاه یا خم‌شده", "۳ × ۱۲ تا ۱۵", "RIR ۰–۱", "۶۰ تا ۹۰ ثانیه", "۱)        ۲)        ۳)"],
            ["A4", "فیس‌پول با طناب", "۳ × ۱۵ تا ۲۰", "RIR ۱–۲", "۶۰ ثانیه", "۱)        ۲)        ۳)"],
            ["A5", "نشر خم دستگاه یا کابل", "۳ × ۱۲ تا ۲۰", "RIR ۱", "۶۰ تا ۹۰ ثانیه", "۱)        ۲)        ۳)"],
            ["A6", "نشر Y روی میز شیب‌دار", "۳ × ۱۲ تا ۱۵", "RIR ۱", "۶۰ ثانیه", "۱)        ۲)        ۳)"],
            ["A7", "چرخش خارجی کابل", "۲ × ۱۵", "سبک", "۴۵ تا ۶۰ ثانیه", "۱)        ۲)"],
            ["د۲", "نشر جانبی کابل (روز پرس)", "۳ × ۱۲ تا ۲۰", "RIR ۱", "۶۰ ثانیه", "۱)        ۲)        ۳)"],
            ["د۲", "نشر خم کابل (روز پرس/پشت)", "۲ تا ۳ × ۱۵ تا ۲۰", "RIR ۱–۲", "۶۰ ثانیه", "۱)        ۲)        ۳)"],
        ],
        [0.06, 0.26, 0.14, 0.11, 0.17, 0.26],
        aligns=["C", "R", "C", "C", "C", "R"],
        rh=8.4,
    )
    pdf.card_row([
        ("پیشروی این هفته", [
            ("هدف: یک تکرار بیشتر از جلسه قبل در هر ست، با همان تکنیک.", DIM),
            ("اگر در همه ست‌ها به سقف بازه رسیدی، جلسه بعد وزنه را ۲.۵ درصد زیاد کن.", DIM),
        ], AMBER),
        ("قانون درد", [
            ("تکنیک درست و دامنه بدون درد، نه بیشتر.", DIM),
            ("اگر درد همان روز از ۳ از ۱۰ گذشت، حرکت را تمام کن.", DIM),
            ("درد شبانه یا ضعف ناگهانی یعنی توقف و ارزیابی تخصصی.", DIM),
        ], ROSE),
    ])
    pdf.box(["تمپو: ۱ ثانیه بالا، ۱ ثانیه توقف اوج، ۲ تا ۳ ثانیه پایین · نشر جانبی: تنه ثابت، بدون شراگ، "
             "دامنه از پشت بدن · هرگز ست سبک را تا نزدیک ناتوانی نزن."],
            bg=TEAL_BG, accent=TEAL, title="یادآوری سریع تکنیک")

    pdf.output(OUT)
    print("ساخته شد:", OUT)


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
شکل‌های خطی تمرین‌ها با یک منبع هندسی مشترک.

هر شکل یک لیست از عناصر ابتدایی است (rect/circle/line/poly/text/arrow/arc)
که دو رندرکننده دارد:
    * to_svg()  -> برای صفحه وب
    * draw_pdf() -> برای PDF (fpdf2)
به این ترتیب هندسه‌ی شکل در دو خروجی کاملاً یکسان می‌ماند و یک بار قابل بازبینی است.

مختصات بر حسب «واحد» است؛ y رو به پایین. زاویه‌ها درجه و در دستگاه صفحه
(۰ درجه = راست، مثبت = پایین) اندازه‌گیری می‌شوند.
"""
import math

# ---------------------------------------------------------------- palette
C_INK = "#2b3446"        # بدن
C_INK2 = "#5c6a83"       # بدن ثانویه / سایه
C_PAD = "#dbe2ec"        # پد و میز
C_FRAME = "#cfd8e6"      # شاسی دستگاه
C_DIM = "#93a0b5"        # خط‌چین حالت شروع
C_AMBER = "#e0a015"      # حرکت هدف
C_AMBER_D = "#a86f00"    # متن تأکید
C_SOFT = "#8a97ab"       # متن راهنما
C_BG = "#ffffff"
C_LINE = "#c9d2e0"
C_ROSE = "#c0483f"
C_TEAL = "#12836f"
C_GREEN = "#1a8a4f"


class Fig:
    def __init__(self, w, h, pad_bg=True):
        self.w, self.h, self.items = w, h, []
        if pad_bg:
            self.rect(0, 0, w, h, fill=C_BG, stroke=C_LINE, sw=1.4, r=14)

    # ------------------------------------------------------- primitives
    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1.6, r=0, dash=None):
        self.items.append(dict(t="rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke,
                               sw=sw, r=r, dash=dash))

    def circle(self, cx, cy, r, fill=None, stroke=None, sw=1.6, dash=None):
        self.items.append(dict(t="circle", x=cx, y=cy, r=r, fill=fill, stroke=stroke,
                               sw=sw, dash=dash))

    def line(self, x1, y1, x2, y2, stroke=C_INK, sw=2.0, dash=None):
        self.items.append(dict(t="line", p=[(x1, y1), (x2, y2)], fill=None, stroke=stroke,
                               sw=sw, dash=dash))

    def poly(self, pts, stroke=None, sw=2.0, fill=None, dash=None, closed=False):
        self.items.append(dict(t="poly", p=list(pts), fill=fill, stroke=stroke, sw=sw,
                               dash=dash, closed=closed))

    def text(self, x, y, s, size=13.5, color=C_SOFT, anchor="middle", weight="normal"):
        self.items.append(dict(t="text", x=x, y=y, s=s, size=size, fill=color,
                               anchor=anchor, weight=weight))

    def badge(self, cx, cy, s, r=11.5, fill=C_GREEN, color="#ffffff", size=12.5):
        self.circle(cx, cy, r, fill=fill)
        self.text(cx, cy + size * 0.36, s, size=size, color=color, anchor="middle",
                  weight="bold")

    def arrow(self, x1, y1, x2, y2, stroke=C_AMBER, sw=2.6, hl=13.0, hw=8.0, dash=None):
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - hl * math.cos(ang), y2 - hl * math.sin(ang)
        self.poly([(x1, y1), (bx, by)], stroke=stroke, sw=sw, dash=dash)
        self.poly([(x2, y2),
                   (bx - hw / 2 * math.sin(ang), by + hw / 2 * math.cos(ang)),
                   (bx + hw / 2 * math.sin(ang), by - hw / 2 * math.cos(ang))],
                  fill=stroke)

    def arc(self, cx, cy, r, a0, a1, stroke=C_AMBER, sw=2.4, dash=None, steps=36,
            head=False, hl=13.0, hw=8.0):
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
                cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps)))
               for i in range(steps + 1)]
        self.poly(pts, stroke=stroke, sw=sw, dash=dash)
        if head:
            (px, py), (qx, qy) = pts[-2], pts[-1]
            ang = math.atan2(qy - py, qx - px)
            bx, by = qx - hl * math.cos(ang), qy - hl * math.sin(ang)
            self.poly([(qx, qy),
                       (bx - hw / 2 * math.sin(ang), by + hw / 2 * math.cos(ang)),
                       (bx + hw / 2 * math.sin(ang), by - hw / 2 * math.cos(ang))],
                      fill=stroke)
        return pts

    def qbez(self, p0, p1, p2, stroke=C_AMBER, sw=2.4, dash=None, steps=28, head=False,
             hl=13.0, hw=8.0):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            u = 1 - t
            pts.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
        self.poly(pts, stroke=stroke, sw=sw, dash=dash)
        if head:
            (px, py), (qx, qy) = pts[-2], pts[-1]
            ang = math.atan2(qy - py, qx - px)
            bx, by = qx - hl * math.cos(ang), qy - hl * math.sin(ang)
            self.poly([(qx, qy),
                       (bx - hw / 2 * math.sin(ang), by + hw / 2 * math.cos(ang)),
                       (bx + hw / 2 * math.sin(ang), by - hw / 2 * math.cos(ang))],
                      fill=stroke)
        return pts

    # -------------------------------------------------------- svg output
    def to_svg(self, cls="fig", label=""):
        o = ['<svg class="%s" viewBox="0 0 %d %d" role="img" aria-label="%s">'
             % (cls, int(self.w), int(self.h), label)]
        o.append('<g font-family="Vazirmatn, Tahoma, sans-serif">')
        for it in self.items:
            t = it["t"]
            dash = ' stroke-dasharray="%g %g"' % (it["dash"], it["dash"] * 0.8) \
                if it.get("dash") else ""
            if t == "rect":
                fill = it["fill"] or "none"
                stroke = it["stroke"] or "none"
                rx = ' rx="%g"' % it["r"] if it["r"] else ""
                o.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" '
                         'stroke="%s" stroke-width="%g"%s%s/>'
                         % (it["x"], it["y"], it["w"], it["h"], fill, stroke, it["sw"],
                            rx, dash))
            elif t == "circle":
                o.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                         'stroke-width="%g"%s/>'
                         % (it["x"], it["y"], it["r"], it["fill"] or "none",
                            it["stroke"] or "none", it["sw"], dash))
            elif t == "line":
                (x1, y1), (x2, y2) = it["p"]
                o.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
                         'stroke-width="%g" stroke-linecap="round"%s/>'
                         % (x1, y1, x2, y2, it["stroke"], it["sw"], dash))
            elif t == "poly":
                pts = " ".join("%g,%g" % p for p in it["p"])
                tag = "polygon" if (it["closed"] or it["fill"]) else "polyline"
                extra = ' stroke-linejoin="round" stroke-linecap="round"'
                if tag == "polygon":
                    extra = ""
                o.append('<%s points="%s" fill="%s" stroke="%s" stroke-width="%g"%s%s/>'
                         % (tag, pts, it["fill"] or "none", it["stroke"] or "none",
                            it["sw"], extra, dash))
            elif t == "text":
                w = ' font-weight="700"' if it["weight"] == "bold" else ""
                o.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'text-anchor="%s" direction="rtl"%s>%s</text>'
                         % (it["x"], it["y"], it["size"], it["fill"],
                            {"middle": "middle", "start": "start", "end": "end"}[it["anchor"]],
                            w, it["s"]))
        o.append("</g></svg>")
        return "\n".join(o)

    # -------------------------------------------------------- pdf output
    def draw_pdf(self, pdf, x0, y0, scale, reshape, fonts=("vz", "vzb")):
        """scale: میلی‌متر به ازای هر واحد شکل."""
        def X(v):
            return x0 + v * scale

        def Y(v):
            return y0 + v * scale

        for it in self.items:
            t = it["t"]
            dash = it.get("dash")
            if dash:
                pdf.set_dash_pattern(dash=dash * scale, gap=dash * scale * 0.8)
            else:
                pdf.set_dash_pattern()
            if it.get("fill"):
                pdf.set_fill_color(*hex2rgb(it["fill"]))
            if it.get("stroke"):
                pdf.set_draw_color(*hex2rgb(it["stroke"]))
                pdf.set_line_width(it["sw"] * scale)
            if t == "rect":
                pdf.rect(X(it["x"]), Y(it["y"]), it["w"] * scale, it["h"] * scale,
                         style="DF" if (it["fill"] and it["stroke"]) else
                               ("F" if it["fill"] else "D"),
                         round_corners=bool(it["r"]), corner_radius=it["r"] * scale)
            elif t == "circle":
                pdf.circle(X(it["x"]), Y(it["y"]), it["r"] * scale,
                           style="DF" if (it["fill"] and it["stroke"]) else
                                 ("F" if it["fill"] else "D"))
            elif t == "line":
                (x1, y1), (x2, y2) = it["p"]
                pdf.line(X(x1), Y(y1), X(x2), Y(y2))
            elif t == "poly":
                pts = [(X(px), Y(py)) for px, py in it["p"]]
                style = "DF" if (it["fill"] and it["stroke"]) else \
                        ("F" if it["fill"] else "D")
                pdf.polygon(pts, style=style)
            elif t == "text":
                pdf.set_font(fonts[1] if it["weight"] == "bold" else fonts[0], "",
                             it["size"] * scale * 2.8346)
                pdf.set_text_color(*hex2rgb(it["fill"]))
                txt = reshape(it["s"])
                w = pdf.get_string_width(txt)
                xx = X(it["x"])
                if it["anchor"] == "middle":
                    xx -= w / 2
                elif it["anchor"] == "end":
                    xx -= w
                pdf.text(xx, Y(it["y"]), txt)
        pdf.set_dash_pattern()


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ================================================================ figures
def fig_a5_setup():
    f = Fig(640, 400)
    # میز و پد
    f.line(30, 372, 610, 372, stroke=C_LINE, sw=2.2)                    # زمین
    f.rect(150, 340, 232, 15, fill=C_FRAME, r=5)                        # نشیمن
    f.rect(150, 355, 26, 17, fill=C_FRAME, r=4)                         # پایه نشیمن
    f.rect(386, 150, 20, 190, fill=C_PAD, r=8)                          # پد سینه
    f.rect(406, 226, 42, 9, fill=C_FRAME, r=3)                          # بازوی نگه‌دارنده
    f.circle(452, 230, 9, fill=C_INK2)                                  # دستگیره
    # پیکر (نمای پهلو، رو به راست)
    f.line(352, 340, 368, 200, stroke=C_INK, sw=38)                     # تنه
    f.circle(384, 170, 19, fill=C_INK)                                  # سر
    f.poly([(382, 168), (404, 176)], stroke=C_INK, sw=30)               # بازو
    f.line(404, 178, 442, 226, stroke=C_INK, sw=22)                     # ساعد
    f.circle(446, 228, 8, fill=C_INK)                                   # دست
    f.line(352, 342, 388, 366, stroke=C_INK2, sw=24)                    # ران
    f.line(388, 366, 388, 370, stroke=C_INK2, sw=20)
    # خط مرجع سطح شانه
    f.line(60, 200, 386, 200, stroke=C_DIM, sw=1.6, dash=6)
    f.text(58, 196, "سطح شانه", size=12.5, color=C_SOFT, anchor="start")
    # شماره مراحل
    f.badge(258, 322, "۱")
    f.badge(432, 154, "۲")
    f.badge(300, 154, "۳")
    # برچسب‌ها
    f.text(632, 96, "پیشانی روی لبه بالای پد،", size=13, anchor="end")
    f.text(632, 114, "گردن در راستای ستون فقرات", size=13, anchor="end")
    f.line(556, 118, 404, 158, stroke=C_DIM, sw=1.4)
    f.text(632, 262, "پد سینه: سینه کامل روی پد", size=13, anchor="end")
    f.line(540, 258, 408, 252, stroke=C_DIM, sw=1.4)
    f.text(30, 250, "دستگیره هم‌ارتفاع شانه؛", size=13, anchor="start")
    f.text(30, 268, "آرنج کمی خم و ثابت", size=13, anchor="start")
    f.line(184, 262, 430, 232, stroke=C_DIM, sw=1.4)
    f.text(30, 356, "پاها ثابت، شکم سفت", size=13, anchor="start")
    return f


def fig_a5_sweep():
    f = Fig(640, 460)
    f.rect(150, 36, 340, 32, fill=C_PAD, r=10)                          # پد
    f.text(320, 26, "پد (سینه و پیشانی) — بالای تصویر جلوی بدن است", size=12.5)
    # پیکر از بالا
    f.rect(284, 246, 72, 126, fill=C_INK, r=34)                         # تنه
    f.circle(320, 396, 25, fill=C_INK)                                  # سر
    f.text(320, 440, "سر", size=12.5)
    # شروع (خط‌چین)
    f.poly([(290, 262), (282, 214), (276, 166)], stroke=C_DIM, sw=17, dash=9)
    f.poly([(350, 262), (358, 214), (364, 166)], stroke=C_DIM, sw=17, dash=9)
    f.circle(276, 162, 9, fill=C_DIM)
    f.circle(364, 162, 9, fill=C_DIM)
    # پایان (حرکت هدف)
    f.poly([(290, 262), (216, 254), (154, 238)], stroke=C_AMBER, sw=17)
    f.poly([(350, 262), (424, 254), (486, 238)], stroke=C_AMBER, sw=17)
    f.circle(150, 236, 10, fill=C_AMBER)
    f.circle(490, 236, 10, fill=C_AMBER)
    # فلش‌های مسیر
    f.qbez((272, 152), (206, 156), (146, 216), sw=2.6, head=True)
    f.qbez((368, 152), (434, 156), (494, 216), sw=2.6, head=True)
    # برچسب‌ها
    f.text(320, 118, "شروع: دست‌ها جلوی بدن، آرنج کمی خم", size=13)
    f.text(632, 300, "پایان: آرنج‌ها به سمت بیرون باز می‌شوند،", size=13, anchor="end")
    f.text(632, 318, "نه با فشار کف دست", size=13, anchor="end")
    f.line(560, 330, 498, 252, stroke=C_DIM, sw=1.4)
    f.text(30, 240, "۱ ثانیه توقف", size=12.5, anchor="start")
    f.text(30, 258, "در نقطه اوج", size=12.5, anchor="start")
    f.line(148, 262, 154, 244, stroke=C_DIM, sw=1.4)
    f.text(320, 440, "برگشت کنترل‌شده ۲ تا ۳ ثانیه — وزنه را رها نکن", size=13)
    f.text(30, 330, "تنه ثابت،", size=12.5, anchor="start")
    f.text(30, 348, "بدون تاب دادن", size=12.5, anchor="start")
    f.line(112, 338, 282, 322, stroke=C_DIM, sw=1.4)
    f.badge(150, 300, "۴")
    f.badge(60, 210, "۵")
    return f


def fig_a6_setup():
    f = Fig(640, 460)
    f.line(30, 420, 610, 420, stroke=C_LINE, sw=2.2)
    # میز شیب‌دار
    f.poly([(250, 330), (430, 170)], stroke=C_PAD, sw=30)
    f.line(268, 336, 268, 420, stroke=C_FRAME, sw=9)
    f.line(412, 190, 412, 420, stroke=C_FRAME, sw=9)
    # پیکر روی میز (نمای پهلو)
    f.poly([(268, 322), (404, 186)], stroke=C_INK, sw=34)               # تنه
    f.circle(432, 158, 20, fill=C_INK)                                  # سر
    f.poly([(266, 330), (232, 372)], stroke=C_INK2, sw=24)              # ران
    f.line(232, 372, 232, 384, stroke=C_INK2, sw=20)
    # بازو: شروع آویزان (خط‌چین) و پایان Y
    f.poly([(404, 196), (410, 240), (414, 282)], stroke=C_DIM, sw=16, dash=9)
    f.circle(416, 292, 10, fill=C_DIM)
    f.poly([(404, 190), (438, 128), (462, 84)], stroke=C_AMBER, sw=16)
    f.circle(468, 74, 11, fill=C_AMBER)
    f.qbez((424, 292), (470, 250), (476, 96), sw=2.6, head=True)
    # برچسب‌ها
    f.text(632, 130, "سینه و شکم کامل روی میز،", size=13, anchor="end")
    f.text(632, 148, "بدون قوس کمر", size=13, anchor="end")
    f.line(560, 164, 356, 248, stroke=C_DIM, sw=1.4)
    f.text(632, 66, "گردن در راستای ستون فقرات؛", size=13, anchor="end")
    f.text(632, 84, "سر را بالا نگیر", size=13, anchor="end")
    f.line(600, 92, 452, 140, stroke=C_DIM, sw=1.4)
    f.text(30, 120, "پایان: دست در مسیر ۴۵ درجه", size=13, anchor="start")
    f.text(30, 138, "بالای سر (شکل Y)", size=13, anchor="start")
    f.line(232, 126, 418, 84, stroke=C_DIM, sw=1.4)
    f.text(30, 300, "شروع: دست آویزان،", size=13, anchor="start")
    f.text(30, 318, "تیغه شانه پایین و عقب", size=13, anchor="start")
    f.line(198, 306, 406, 268, stroke=C_DIM, sw=1.4)
    f.text(320, 442, "مسیر حرکت: از پایین به بالا و جلو — نه به طرفین", size=13)
    f.badge(238, 220, "۲")
    f.badge(500, 200, "۵")
    return f


def fig_a6_shape():
    f = Fig(640, 460)
    f.rect(280, 148, 80, 250, fill=C_INK, r=36)                         # تنه (نمای پشت)
    f.circle(320, 118, 26, fill=C_INK)                                  # سر
    # بازوها در حالت Y
    f.poly([(294, 172), (232, 106), (176, 50)], stroke=C_AMBER, sw=17)
    f.poly([(346, 172), (408, 106), (464, 50)], stroke=C_AMBER, sw=17)
    f.circle(170, 44, 11, fill=C_AMBER)
    f.circle(470, 44, 11, fill=C_AMBER)
    # حالت آویزان (خط‌چین)
    f.poly([(294, 172), (272, 268), (266, 356)], stroke=C_DIM, sw=15, dash=9)
    f.poly([(346, 172), (368, 268), (374, 356)], stroke=C_DIM, sw=15, dash=9)
    # زاویه ۴۵ درجه
    f.line(294, 172, 294, 40, stroke=C_DIM, sw=1.5, dash=6)
    f.arc(294, 172, 78, -90, -40, stroke=C_TEAL, sw=2.2, head=True, hl=11, hw=7)
    f.text(258, 66, "۴۵°", size=13.5, color=C_TEAL, weight="bold")
    # فلش مسیر
    f.qbez((272, 344), (188, 300), (168, 74), sw=2.6, head=True)
    # برچسب‌ها
    f.text(320, 440, "در دید از روبه‌رو، دست‌ها شکل Y می‌سازند", size=13)
    f.text(632, 250, "آرنج کمی خم و در کل ست ثابت", size=13, anchor="end")
    f.line(556, 266, 320, 210, stroke=C_DIM, sw=1.4)
    f.text(632, 330, "تیغه‌های شانه پایین و عقب (دور از گوش)", size=13, anchor="end")
    f.line(556, 346, 368, 302, stroke=C_DIM, sw=1.4)
    f.text(30, 250, "گریپ خنثی،", size=13, anchor="start")
    f.text(30, 268, "شست رو به بالا", size=13, anchor="start")
    f.line(162, 262, 170, 80, stroke=C_DIM, sw=1.4)
    f.text(30, 388, "هرگز با وزنه سنگین؛", size=13, anchor="start")
    f.text(30, 406, "این حرکت با شراگ اشتباه می‌شود", size=13, anchor="start")
    f.badge(560, 150, "۳")
    return f


def fig_a7_setup():
    f = Fig(640, 400)
    f.line(30, 372, 610, 372, stroke=C_LINE, sw=2.2)
    f.rect(524, 90, 22, 282, fill=C_FRAME, r=6)                          # ستون دستگاه
    f.circle(524, 240, 9, fill=C_INK2)                                   # قرقره
    f.line(516, 240, 430, 240, stroke=C_DIM, sw=3.0, dash=7)             # کابل
    # پیکر (نمای پهلو، رو به راست)
    f.line(268, 348, 278, 196, stroke=C_INK, sw=36)                      # تنه
    f.circle(288, 166, 19, fill=C_INK)                                   # سر
    f.line(268, 350, 262, 372, stroke=C_INK2, sw=24)                     # ران و ساق
    f.line(262, 372, 282, 372, stroke=C_INK2, sw=20)
    f.line(282, 206, 288, 246, stroke=C_INK, sw=22)                      # بازو (چسبیده به پهلو)
    f.rect(296, 232, 13, 30, fill="#e8b04b", r=5)                        # حوله
    f.line(288, 248, 424, 240, stroke=C_INK, sw=18)                      # ساعد
    f.circle(430, 240, 9, fill=C_INK)                                    # مچ و دست
    # جهت چرخش (از دید ناظر: دور شدن از بیننده)
    f.arc(398, 214, 26, 150, 30, stroke=C_AMBER, sw=2.4, head=True, hl=11, hw=7)
    f.text(414, 200, "به سمت بیرون", size=12.5, color=C_AMBER_D)
    # برچسب‌ها
    f.text(632, 214, "آرنج ۹۰ درجه، چسبیده به پهلو", size=13, anchor="end")
    f.line(560, 224, 306, 250, stroke=C_DIM, sw=1.4)
    f.text(632, 300, "قرقره هم‌ارتفاع آرنج", size=13, anchor="end")
    f.line(556, 306, 534, 246, stroke=C_DIM, sw=1.4)
    f.text(30, 120, "شانه پایین و عقب؛", size=13, anchor="start")
    f.text(30, 138, "بدون بالا کشیدن شانه", size=13, anchor="start")
    f.line(180, 126, 282, 196, stroke=C_DIM, sw=1.4)
    f.text(30, 300, "حوله کوچک بین آرنج و پهلو", size=13, anchor="start")
    f.line(214, 306, 298, 248, stroke=C_DIM, sw=1.4)
    f.text(320, 356, "مچ صاف و ثابت، حرکت فقط از ساعد", size=13)
    f.badge(190, 230, "۲")
    return f


def fig_a7_rotation():
    f = Fig(640, 440)
    # پیکر از بالا (سر پایین، رو به بالا = جلوی بدن)
    f.circle(320, 396, 25, fill=C_INK)                                   # سر
    f.text(320, 440, "سر — پایین تصویر", size=12.5)
    f.rect(284, 250, 72, 122, fill=C_INK, r=34)                          # تنه
    # بازوی کارکننده: بازو چسبیده به پهلو
    f.line(292, 268, 276, 318, stroke=C_INK, sw=20)
    # ساعد: شروع (رو به شکم) خط‌چین
    f.poly([(276, 318), (322, 292)], stroke=C_DIM, sw=16, dash=9)
    f.circle(330, 289, 9, fill=C_DIM)
    # ساعد: پایان (به سمت بیرون)
    f.poly([(276, 318), (216, 292)], stroke=C_AMBER, sw=16)
    f.circle(208, 289, 10, fill=C_AMBER)
    # کمان چرخش
    f.arc(276, 318, 76, -24, -150, stroke=C_AMBER, sw=2.4, head=True, hl=12, hw=8)
    # برچسب‌ها
    f.text(632, 216, "شروع: ساعد رو به شکم", size=13, anchor="end")
    f.text(632, 234, "(چرخش داخلی)", size=13, anchor="end")
    f.line(524, 250, 344, 284, stroke=C_DIM, sw=1.4)
    f.text(30, 216, "پایان: ساعد به سمت بیرون", size=13, anchor="start")
    f.text(30, 234, "(چرخش خارجی)", size=13, anchor="start")
    f.line(196, 252, 206, 286, stroke=C_DIM, sw=1.4)
    f.text(320, 26, "نمای از بالا — چرخش فقط در مفصل آرنج انجام می‌شود", size=12.5)
    f.text(632, 352, "آرنج از پهلو جدا نمی‌شود", size=13, anchor="end")
    f.line(556, 346, 310, 320, stroke=C_DIM, sw=1.4)
    f.text(30, 368, "تنه ثابت؛", size=13, anchor="start")
    f.text(30, 386, "بدون تاب دادن", size=13, anchor="start")
    f.line(126, 376, 282, 360, stroke=C_DIM, sw=1.4)
    f.text(470, 400, "۱ ثانیه توقف در پایان", size=12.5, color=C_AMBER_D)
    return f


FIGURES = {
    "a5_setup": fig_a5_setup,
    "a5_sweep": fig_a5_sweep,
    "a6_setup": fig_a6_setup,
    "a6_shape": fig_a6_shape,
    "a7_setup": fig_a7_setup,
    "a7_rotation": fig_a7_rotation,
}


if __name__ == "__main__":
    for k, fn in FIGURES.items():
        fig = fn()
        svg = fig.to_svg(label=k)
        print(k, "items:", len(fig.items), "svg bytes:", len(svg))

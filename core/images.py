# -*- coding: utf-8 -*-
"""موتور طراحی تصویر پست و استوری با Pillow — کاملاً آفلاین"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import arabic_reshaper
from bidi.algorithm import get_display

from .content import fa_num, fa_price

FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"

FONT_PATHS = {
    "regular": FONT_DIR / "Vazirmatn-Regular.ttf",
    "medium": FONT_DIR / "Vazirmatn-Medium.ttf",
    "semibold": FONT_DIR / "Vazirmatn-SemiBold.ttf",
    "bold": FONT_DIR / "Vazirmatn-Bold.ttf",
    "black": FONT_DIR / "Vazirmatn-Black.ttf",
}
_font_cache = {}


def font(weight="regular", size=40):
    key = (weight, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONT_PATHS.get(weight, FONT_PATHS["regular"])), size)
    return _font_cache[key]


def shaped(text):
    return get_display(arabic_reshaper.reshape(str(text)))


def hex_rgb(value, default=(124, 58, 237)):
    try:
        v = str(value).lstrip("#")
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return default


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_bg(size, c1, c2):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        row = lerp(c1, c2, t)
        for x in range(w):
            px[x, y] = row
    return img


def draw_decor(img, c1, c2, seed=7):
    """دایره‌های محو تزئینی"""
    rnd = random.Random(seed)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = img.size
    for i in range(4):
        r = rnd.randint(int(w * 0.12), int(w * 0.30))
        x = rnd.randint(-r // 2, w - r // 2)
        y = rnd.randint(-r // 2, h - r // 2)
        col = tuple(c2) + (rnd.randint(14, 30),) if i % 2 == 0 else tuple(c1) + (rnd.randint(14, 30),)
        d.ellipse([x, y, x + r, y + r], fill=col)
    overlay = overlay.filter(ImageFilter.GaussianBlur(3))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))
    return img


def wrap_lines(draw, text, fnt, max_w):
    lines, cur = [], ""
    for part in str(text).split("\n"):
        for word in part.split(" "):
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=fnt) <= max_w or not cur:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        cur = ""
    return lines


def fit_font(draw, text, max_w, start, min_size, weight="bold"):
    size = start
    while size > min_size:
        fnt = font(weight, size)
        if draw.textlength(shaped(text), font=fnt) <= max_w:
            return fnt
        size -= 2
    return font(weight, min_size)


def draw_center(draw, cx, y, text, fnt, fill, max_w=None):
    t = shaped(text)
    if max_w and draw.textlength(t, font=fnt) > max_w:
        fnt = fit_font(draw, t, max_w, fnt.size, max(18, fnt.size // 2))
    w = draw.textlength(t, font=fnt)
    draw.text((cx - w / 2, y), t, font=fnt, fill=fill)
    bbox = draw.textbbox((cx - w / 2, y), t, font=fnt)
    return bbox


def draw_right(draw, x_right, y, text, fnt, fill):
    t = shaped(text)
    w = draw.textlength(t, font=fnt)
    draw.text((x_right - w, y), t, font=fnt, fill=fill)
    return w


def draw_pill(draw, cx, y, text, fnt, text_color, bg_color, pad_x=36, pad_y=16, radius=None):
    t = shaped(text)
    w = draw.textlength(t, font=fnt)
    h = fnt.size + pad_y * 2
    radius = radius if radius is not None else h // 2
    x0, y0 = cx - w / 2 - pad_x, y
    x1, y1 = cx + w / 2 + pad_x, y + h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=bg_color)
    draw.text((cx - w / 2, y + pad_y), t, font=fnt, fill=text_color)
    return x0, y0, x1, y1


def rounded_img(img, radius=28):
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def cover_fit(img, w, h):
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))), Image.LANCZOS)
    left = (img.width - w) // 2
    top = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def draw_icon(draw, name, cx, cy, size, color):
    """آیکون‌های ساده وکتوری"""
    s = size / 2
    if name == "star":
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            r = s if i % 2 == 0 else s * 0.45
            pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
        draw.polygon(pts, fill=color)
    elif name == "heart":
        r = s * 0.42
        draw.ellipse([cx - s * 0.55, cy - s * 0.55, cx - s * 0.55 + 2 * r, cy - s * 0.55 + 2 * r], fill=color)
        draw.ellipse([cx + s * 0.55 - 2 * r, cy - s * 0.55, cx + s * 0.55, cy - s * 0.55 + 2 * r], fill=color)
        draw.polygon([(cx - s * 0.62, cy - s * 0.18), (cx + s * 0.62, cy - s * 0.18), (cx, cy + s * 0.62)], fill=color)
    elif name == "cart":
        draw.rounded_rectangle([cx - s, cy - s * 0.5, cx + s * 0.4, cy + s * 0.3], radius=s * 0.18, fill=color)
        draw.polygon([(cx - s, cy - s * 0.5), (cx - s * 0.65, cy + s * 0.3), (cx + s * 0.05, cy + s * 0.3)], fill=color)
        draw.ellipse([cx - s * 0.7, cy + s * 0.15, cx - s * 0.3, cy + s * 0.55], fill=color)
        draw.ellipse([cx - s * 0.05, cy + s * 0.15, cx + s * 0.35, cy + s * 0.55], fill=color)
    elif name == "gift":
        draw.rectangle([cx - s * 0.7, cy - s * 0.35, cx + s * 0.7, cy + s * 0.6], fill=color)
        draw.rectangle([cx - s * 0.1, cy - s * 0.35, cx + s * 0.1, cy + s * 0.6], fill=(255, 255, 255))
        draw.rectangle([cx - s * 0.7, cy - s * 0.12, cx + s * 0.7, cy + s * 0.12], fill=(255, 255, 255))
        draw.ellipse([cx - s * 0.28, cy - s * 0.62, cx - s * 0.02, cy - s * 0.30], fill=color)
        draw.ellipse([cx + s * 0.02, cy - s * 0.62, cx + s * 0.28, cy - s * 0.30], fill=color)
    elif name == "bulb":
        draw.ellipse([cx - s * 0.55, cy - s * 0.8, cx + s * 0.55, cy + s * 0.3], fill=color)
        draw.rectangle([cx - s * 0.25, cy + s * 0.3, cx + s * 0.25, cy + s * 0.55], fill=color)
        for ang in range(0, 360, 45):
            x0 = cx + (s * 0.95) * math.cos(math.radians(ang))
            y0 = cy - s * 0.25 + (s * 0.95) * math.sin(math.radians(ang))
            x1 = cx + (s * 1.2) * math.cos(math.radians(ang))
            y1 = cy - s * 0.25 + (s * 1.2) * math.sin(math.radians(ang))
            draw.line([x0, y0, x1, y1], fill=color, width=max(3, int(s * 0.08)))
    elif name == "tag":
        draw.rounded_rectangle([cx - s * 0.7, cy - s * 0.6, cx + s * 0.7, cy + s * 0.6], radius=s * 0.16, fill=color)
        draw.ellipse([cx - s * 0.16, cy - s * 0.16, cx + s * 0.16, cy + s * 0.16], fill=(255, 255, 255))
    elif name == "chat":
        draw.rounded_rectangle([cx - s, cy - s * 0.65, cx + s, cy + s * 0.35], radius=s * 0.22, fill=color)
        draw.polygon([(cx - s * 0.35, cy + s * 0.32), (cx - s * 0.55, cy + s * 0.72), (cx + s * 0.05, cy + s * 0.35)], fill=color)
    elif name == "percent":
        f = font("black", int(size * 1.5))
        t = shaped("٪")
        w = draw.textlength(t, font=f)
        draw.text((cx - w / 2, cy - size * 0.75), t, font=f, fill=color)


class PostRenderer:
    """رندر پست (1080x1080) و استوری (1080x1920)"""

    def __init__(self, shop):
        self.shop = shop
        self.name = shop.get("name", "فروشگاه من")
        self.handle = shop.get("handle", "")
        self.phone = shop.get("phone", "")
        self.tagline = shop.get("tagline", "")
        self.c1 = hex_rgb(shop.get("color1"))
        self.c2 = hex_rgb(shop.get("color2"))
        self.accent = hex_rgb(shop.get("accent"), (251, 191, 36))
        self.dark = (30, 27, 48)
        self.muted = (105, 103, 125)

    # ---------- اجزای مشترک ----------
    def header(self, d, w, is_story=False, scale=1.0):
        top = int(240 * scale) if is_story else int(64 * scale)
        name_f = fit_font(d, self.name, int(w * 0.8), int(44 * scale), int(28 * scale), "black")
        draw_center(d, w / 2, top, self.name, name_f, (255, 255, 255))
        if self.tagline:
            tag_f = font("regular", int(28 * scale))
            draw_center(d, w / 2, top + name_f.size + int(14 * scale),
                        self.tagline, tag_f, (255, 255, 255, 200))
        if self.handle:
            hf = font("semibold", int(26 * scale))
            draw_pill(d, w / 2, top + int(92 * scale), "@" + self.handle, hf,
                      self.dark, self.accent, pad_x=26, pad_y=10)

    def footer(self, d, w, h, is_story=False, scale=1.0):
        fnt = font("medium", int(30 * scale))
        lines = []
        if self.handle:
            lines.append(self.handle)
        if self.phone:
            lines.append("تلفن: " + fa_num(self.phone))
        if is_story:
            y = int(1560 * scale)
        else:
            y = h - int(46 * scale) - (len(lines) - 1) * int(40 * scale)
        for line in lines:
            draw_center(d, w / 2, y, line, fnt, (255, 255, 255, 210))
            y += int(40 * scale)

    def cta_button(self, d, w, cy, scale=1.0):
        cta = self.shop.get("cta", "برای سفارش دایرکت بده")
        fnt = font("bold", int(40 * scale))
        draw_pill(d, w / 2, cy, cta, fnt, (255, 255, 255), self.c1,
                  pad_x=48, pad_y=20, radius=999)

    def render(self, kind="post", template="product", product=None, title="",
               text="", price="", old_price="", extra="", icon="tag", out_path=None):
        product = product or {}
        W, H = (1080, 1080) if kind == "post" else (1080, 1920)
        is_story = kind == "story"
        scale = 1.0
        img = gradient_bg((W, H), self.c1, self.c2)
        img = draw_decor(img, self.c1, self.c2, seed=random.randint(1, 9999))
        d = ImageDraw.Draw(img)

        self.header(d, W, is_story=is_story, scale=scale)

        # ---------- کارت اصلی ----------
        margin = int(80 * scale)
        if is_story:
            card_h = int(1080 * scale)
            card_y = int(440 * scale)
        else:
            card_h = H - 320
            card_y = int(250 * scale)
        card_x = margin
        card_w = W - 2 * margin
        d.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                            radius=44, fill=(247, 247, 252))
        cx = W / 2
        cur_y = card_y

        if template == "product":
            img_area_h = int(470 * scale) if kind == "post" else int(600 * scale)
            has_img = False
            if product.get("image_path") and Path(product["image_path"]).exists():
                try:
                    pimg = Image.open(product["image_path"]).convert("RGB")
                    pimg = cover_fit(pimg, card_w - 68, img_area_h)
                    rimg = rounded_img(pimg, radius=30)
                    img.paste(rimg, (card_x + 34, cur_y + 36), rimg)
                    cur_y += 36 + img_area_h
                    has_img = True
                except Exception:
                    has_img = False
            if not has_img:
                draw_icon(d, icon, cx, cur_y + img_area_h / 2 - 14, 175, self.c1)
                cur_y += img_area_h

            title = title or product.get("name", "")
            if title:
                tf = fit_font(d, title, card_w - 110, int(60 * scale) if kind == "post" else int(66 * scale),
                              int(34 * scale), "black")
                bbox = draw_center(d, cx, cur_y + int(36 * scale), title, tf, self.dark)
                cur_y = bbox[3]
            if text:
                xf = font("regular", int(36 * scale) if kind == "post" else int(40 * scale))
                lines = wrap_lines(d, shaped(text), xf, card_w - 130)
                lines = lines[:2 if kind == "post" else 3]
                y = cur_y + int(28 * scale)
                for ln in lines:
                    draw_center(d, cx, y, ln, xf, self.muted)
                    y += int(xf.size * 1.5)
                cur_y = y - int(20 * scale)
            if price:
                pf = font("bold", int(44 * scale) if kind == "post" else int(50 * scale))
                bbox = draw_pill(d, cx, cur_y + int(30 * scale), fa_price(price), pf,
                                 self.dark, self.accent, pad_x=40, pad_y=18)
                cur_y = bbox[3] + int(24 * scale)
            else:
                cur_y += int(40 * scale)
            self.cta_button(d, W, min(cur_y + int(36 * scale), card_y + card_h - int(120 * scale)), scale)

        elif template == "offer":
            # نوار تخفیف
            d.rounded_rectangle([card_x + 34, cur_y + 36, card_x + card_w - 34, cur_y + 36 + int(118 * scale)],
                                radius=30, fill=self.accent)
            of = font("black", int(56 * scale))
            draw_center(d, cx, cur_y + 36 + int(24 * scale), extra or "پیشنهاد ویژه",
                        of, self.dark)
            cur_y += 36 + int(118 * scale) + int(30 * scale)

            if product.get("image_path") and Path(product["image_path"]).exists():
                try:
                    pimg = Image.open(product["image_path"]).convert("RGB")
                    pimg = cover_fit(pimg, card_w - 68, int(330 * scale))
                    rimg = rounded_img(pimg, radius=30)
                    img.paste(rimg, (card_x + 34, cur_y), rimg)
                    cur_y += int(330 * scale) + int(34 * scale)
                except Exception:
                    pass
            title = title or product.get("name", "")
            if title:
                tf = fit_font(d, title, card_w - 110, int(62 * scale), int(36 * scale), "black")
                cur_y = draw_center(d, cx, cur_y, title, tf, self.dark)[3]
            if text:
                xf = font("regular", int(36 * scale))
                for ln in wrap_lines(d, shaped(text), xf, card_w - 130)[:2]:
                    cur_y = draw_center(d, cx, cur_y + int(20 * scale), ln, xf, self.muted)[3]
            if price:
                pf = font("bold", int(52 * scale))
                # قیمت قبلی خط‌خورده
                if old_price:
                    of_ = font("medium", int(38 * scale))
                    t = shaped(fa_price(old_price))
                    w_ = d.textlength(t, font=of_)
                    b = draw_center(d, cx, cur_y + int(34 * scale), fa_price(old_price), of_, self.muted)
                    d.line([b[0] + 4, (b[1] + b[3]) / 2, b[2] - 4, (b[1] + b[3]) / 2],
                           fill=(180, 60, 60), width=4)
                    cur_y = b[3] + int(8 * scale)
                bbox = draw_pill(d, cx, cur_y + int(26 * scale), fa_price(price), pf,
                                 self.dark, self.accent, pad_x=42, pad_y=18)
                cur_y = bbox[3] + int(26 * scale)
            self.cta_button(d, W, min(cur_y + int(30 * scale), card_y + card_h - int(120 * scale)), scale)

        else:
            # قالب‌های متنی (tip / quote / question) — عمدتاً استوری
            icon_map = {"tip": "bulb", "quote": "heart", "question": "chat"}
            label_map = {"tip": "نکته روز", "quote": "یک جمله برای امروز", "question": "سوال امروز"}
            icon_name = icon_map.get(template, "bulb")
            draw_icon(d, icon_name, cx, cur_y + int(190 * scale), 130, self.accent)
            cur_y += int(360 * scale)
            label = label_map.get(template, "نکته روز")
            lf = font("bold", int(38 * scale))
            draw_center(d, cx, cur_y, label, lf, self.c1)
            cur_y += int(80 * scale)
            main = extra or text or title or (product.get("description") or "")
            tf = fit_font(d, main, card_w - 150, int(56 * scale), int(34 * scale), "bold")
            max_lines = 2 if not is_story else 5
            lines = wrap_lines(d, shaped(main), tf, card_w - 150)[:max_lines]
            y = cur_y
            for ln in lines:
                bbox = draw_center(d, cx, y, ln, tf, self.dark)
                y = bbox[3] + int(46 * scale)
            cur_y = y + int(30 * scale)
            if template == "question" and cur_y + int(150 * scale) <= card_y + card_h:
                self.cta_button(d, W, cur_y + int(40 * scale), scale)

        self.footer(d, W, H, is_story=is_story, scale=scale)

        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(out_path, "JPEG", quality=92)
        return img

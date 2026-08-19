# -*- coding: utf-8 -*-
"""Remove the flat navy background from logo_raw.png -> logo.png (transparent)."""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

im = Image.open("logo_raw.png").convert("RGB")
a = np.asarray(im).astype(int)
h, w, _ = a.shape

# sample background color from corners
corners = np.array([a[3, 3], a[3, -4], a[-4, 3], a[-4, -4]])
bgc = corners.mean(axis=0)

dist = np.sqrt(((a - bgc) ** 2).sum(axis=2))
bg_like = dist < 55  # tolerant of vignette

# keep only bg-like pixels connected to the border
lbl, n = ndimage.label(bg_like)
border_labels = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])))
border_labels.discard(0)
mask_bg = np.isin(lbl, list(border_labels))

alpha = np.where(mask_bg, 0, 255).astype(np.uint8)
alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.2))

out = im.convert("RGBA")
out.putalpha(alpha_img)

# crop to content
bbox = out.getbbox()
out = out.crop(bbox)
out.save("logo.png")
print("logo.png", out.size)

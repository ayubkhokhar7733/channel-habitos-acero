#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
thumbnail_gen.py — Automated Full HD (1920x1080) High-CTR YouTube Thumbnail Generator.

Features:
- Renders authentic speaker cutout on right side (with smooth edge feathering & studio rim glow).
- Builds cinematic studio dark charcoal gradient on the text side.
- Renders high-impact 3D Montserrat-ExtraBold headline hook typography (alternating Yellow/White).
- Renders official Speaker Authority Badge with studio podcast microphone icon.
- Falls back cleanly to 1280x720 base if assets are unavailable.
"""

import os
import sys
import re
import random
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config

THUMB_WIDTH = 1920
THUMB_HEIGHT = 1080

COLOR_MAP = {
    "white": (255, 255, 255, 255),
    "yellow": (255, 224, 38, 255),
    "gold": (255, 214, 48, 255),
    "red": (242, 24, 28, 255),
}


def _extract_short_hook_text(topic: str) -> list:
    """Extract 2-4 punchy words split across 2-3 short lines for high-CTR thumbnails."""
    clean = re.sub(r'[:\-–—|].*$', '', topic).strip()  # remove subtitle/speaker suffix
    clean = re.sub(r'[¿?¡!]', '', clean).strip()
    words = clean.split()
    if not words:
        return ["EL SECRETO", "DE TU MENTE"]

    # If already 2-4 words, split naturally
    if len(words) == 2:
        return [words[0].upper(), words[1].upper()]
    elif len(words) == 3:
        return [words[0].upper(), f"{words[1]} {words[2]}".upper()]
    elif len(words) == 4:
        return [f"{words[0]} {words[1]}".upper(), f"{words[2]} {words[3]}".upper()]
    elif len(words) <= 6:
        mid = len(words) // 2
        return [" ".join(words[:mid]).upper(), " ".join(words[mid:]).upper()]
    else:
        # Take first 5 punchy words
        return [" ".join(words[:3]).upper(), " ".join(words[3:6]).upper()]


def _get_font(size: int, bold: bool = True):
    repo_root = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(repo_root, "assets", "Montserrat-ExtraBold.ttf"),
        os.path.join(repo_root, "assets", "Montserrat-Bold.ttf"),
        getattr(config, "FONT_PATH", ""),
        "Montserrat-ExtraBold.ttf",
        "Montserrat-Bold.ttf",
        "impact.ttf",
        "arialbd.ttf",
        "segoeuib.ttf",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_mic_icon(draw, cx, cy, size=22, color=(212, 24, 32, 255)):
    cap_w = size * 0.48
    cap_h = size * 0.86
    cx0 = cx - cap_w / 2
    cy0 = cy - size * 0.62
    cx1 = cx + cap_w / 2
    cy1 = cy0 + cap_h
    draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=int(cap_w / 2), fill=color)

    stroke = max(3, round(size * 0.12))
    arc_r = size * 0.44
    arc_top = cy0 + cap_h * 0.35
    arc_bot = cy1 + size * 0.22
    draw.arc([cx - arc_r, arc_top, cx + arc_r, arc_bot], start=0, end=180, fill=color, width=stroke)

    stem_top = arc_bot - 1
    stem_bot = stem_top + size * 0.26
    draw.line([(cx, stem_top), (cx, stem_bot)], fill=color, width=stroke)
    base_half = size * 0.32
    draw.line([(cx - base_half, stem_bot), (cx + base_half, stem_bot)], fill=color, width=stroke)


def draw_clean_headline(draw, pos, text, font, fill, contour_px=4, contour_color=(12, 14, 20, 240), shadow_offset=(6, 8)):
    x, y = pos
    sx, sy = shadow_offset
    draw.text((x + sx, y + sy), text, font=font, fill=(5, 6, 10, 235))
    draw.text((x + sx + 2, y + sy + 3), text, font=font, fill=(5, 6, 10, 150))
    if contour_px > 0:
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            stroke_width=contour_px,
            stroke_fill=contour_color,
        )
    else:
        draw.text((x, y), text, font=font, fill=fill)


def _build_studio_bg(W: int, H: int) -> Image.Image:
    y_coords = np.linspace(0, 1, H)
    stops_y = np.array([0.0, 0.30, 0.65, 1.0])
    stops_r = np.array([38, 24, 16, 10])
    stops_g = np.array([42, 26, 18, 12])
    stops_b = np.array([52, 34, 24, 16])

    grad_r = np.interp(y_coords, stops_y, stops_r).astype(np.uint8)
    grad_g = np.interp(y_coords, stops_y, stops_g).astype(np.uint8)
    grad_b = np.interp(y_coords, stops_y, stops_b).astype(np.uint8)

    grad_col = np.stack([grad_r, grad_g, grad_b], axis=1)
    grad_arr = np.broadcast_to(grad_col[:, None, :], (H, W, 3)).copy()
    return Image.fromarray(grad_arr, mode="RGB").convert("RGBA")


def generate_thumbnail(
    topic: str,
    output_path: str = None,
    background_image_path: str = None,
    overlay_text: str = None,
    badge_text: str = "DR MARIO",
    speaker_cutout_path: str = None,
) -> str:
    W, H = THUMB_WIDTH, THUMB_HEIGHT
    repo_root = os.path.dirname(os.path.abspath(__file__))

    if not output_path:
        safe_topic = re.sub(r'[^a-zA-Z0-9]+', '-', topic).strip('-').lower()[:40]
        output_path = os.path.join(getattr(config, "OUTPUT_DIR", "output"), f"thumb_{safe_topic}.jpg")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # 1. Base Studio Canvas
    canvas = _build_studio_bg(W, H)

    # 2. Add subtle cinematic background lighting/texture if available
    if background_image_path and os.path.exists(background_image_path):
        try:
            bg_sub = Image.open(background_image_path).convert("RGBA")
            bg_sub = bg_sub.resize((W, H), Image.Resampling.LANCZOS)
            bg_sub = ImageEnhance.Color(bg_sub).enhance(0.4)
            bg_sub = ImageEnhance.Brightness(bg_sub).enhance(0.35)
            canvas = Image.alpha_composite(canvas, bg_sub)
        except Exception as e:
            print(f"[thumbnail_gen] Note on bg_sub: {e}")

    # 3. Locate and Composite Speaker Cutout on Right Side
    cutout_candidates = [
        speaker_cutout_path,
        os.path.join(repo_root, "assets", "speaker_cutout.png"),
        os.path.join(repo_root, "assets", "speaker_portrait.png"),
    ]
    cutout_file = None
    for c in cutout_candidates:
        if c and os.path.exists(c) and os.path.getsize(c) > 5000:
            cutout_file = c
            break

    if cutout_file:
        try:
            speaker_img = Image.open(cutout_file).convert("RGBA")
            # Scale portrait to fit right half (approx 900-1000px wide, up to H)
            orig_w, orig_h = speaker_img.size
            target_h = int(H * 0.98)
            scale = target_h / orig_h
            target_w = int(orig_w * scale)
            speaker_resized = speaker_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # Place portrait flush-right
            pos_x = W - target_w + 30
            pos_y = H - target_h

            # Soft drop shadow / dark halo behind speaker
            shadow_mask = speaker_resized.split()[3]
            halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            halo_draw = ImageDraw.Draw(halo)
            halo_draw.bitmap((pos_x - 15, pos_y + 10), shadow_mask, fill=(0, 0, 0, 180))
            halo = halo.filter(ImageFilter.GaussianBlur(radius=18))
            canvas = Image.alpha_composite(canvas, halo)

            # Paste speaker
            spk_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            spk_layer.paste(speaker_resized, (pos_x, pos_y), speaker_resized)
            canvas = Image.alpha_composite(canvas, spk_layer)
            print(f"[thumbnail_gen] Composed speaker portrait from {cutout_file} at ({pos_x}, {pos_y})")
        except Exception as e:
            print(f"[thumbnail_gen] Speaker cutout composition failed: {e}")

    # 4. Typography Layer
    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    if overlay_text:
        lines = [line.strip().upper() for line in overlay_text.split("\n") if line.strip()]
    else:
        lines = _extract_short_hook_text(topic)
    lines = lines[:3]

    text_center_x = 580  # Center of left 60% text column
    max_col_w = 980
    font_size = 130 if len(lines) <= 2 else 114
    while font_size > 68:
        test_font = _get_font(font_size)
        widest = max((draw.textbbox((0, 0), t.upper(), font=test_font)[2] for t in lines), default=0)
        if widest <= max_col_w:
            break
        font_size -= 6

    font_main = _get_font(font_size)
    line_step = int(font_size * 1.22)
    total_text_h = line_step * len(lines)
    y_start = max(110, (H - 180 - total_text_h) // 2)

    line_colors = ["yellow", "white", "yellow"]
    for idx, raw_text in enumerate(lines):
        t = raw_text.strip().upper()
        cname = line_colors[idx % len(line_colors)]
        fill = COLOR_MAP.get(cname.lower(), COLOR_MAP["white"])
        bbox = draw.textbbox((0, 0), t, font=font_main)
        lw = bbox[2] - bbox[0]
        x_pos = text_center_x - lw // 2 - bbox[0]
        y_pos = y_start + idx * line_step

        draw_clean_headline(draw, (x_pos, y_pos), t, font=font_main, fill=fill, contour_px=4, shadow_offset=(6, 8))

    # 5. Official Speaker Authority Pill Badge
    font_badge = _get_font(38)
    b_text = badge_text.strip().upper() if badge_text else "OFICIAL"
    tbbox = draw.textbbox((0, 0), b_text, font=font_badge)
    tw, th = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]

    pill_h = 84
    mic_area_w = 72
    pad_left = 22
    pad_right = 34
    pill_w = pad_left + mic_area_w + tw + pad_right
    px0 = text_center_x - pill_w // 2
    py0 = H - 150
    px1 = px0 + pill_w
    py1 = py0 + pill_h

    # Shadow for pill
    shadow_pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_pill).rounded_rectangle([px0 + 4, py0 + 8, px1 + 4, py1 + 8], radius=pill_h // 2, fill=(0, 0, 0, 175))
    shadow_pill = shadow_pill.filter(ImageFilter.GaussianBlur(radius=6))
    canvas = Image.alpha_composite(canvas, shadow_pill)

    # Pill body & outline
    draw.rounded_rectangle([px0, py0, px1, py1], radius=pill_h // 2, fill=(212, 22, 30, 255), outline=(255, 224, 64, 240), width=3)
    mic_cx = px0 + pad_left + 27
    mic_cy = (py0 + py1) // 2
    draw.ellipse([mic_cx - 27, mic_cy - 27, mic_cx + 27, mic_cy + 27], fill=(255, 255, 255, 255))
    draw_mic_icon(draw, mic_cx, mic_cy, size=24, color=(212, 22, 30, 255))

    tx = px0 + pad_left + mic_area_w + 4
    ty = py0 + (pill_h - th) // 2 - tbbox[1]
    draw.text((tx + 2, ty + 2), b_text, font=font_badge, fill=(75, 0, 0, 190))
    draw.text((tx, ty), b_text, font=font_badge, fill=(255, 255, 255, 255))

    # 6. Compose and Save
    final = Image.alpha_composite(canvas, txt_layer).convert("RGB")
    final.save(output_path, "JPEG", quality=96, subsampling=0)
    print(f"✅ Created Studio HD thumbnail: {output_path} ({final.size[0]}x{final.size[1]}, {os.path.getsize(output_path)/1024:.1f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="YouTube Thumbnail Generator CLI.")
    parser.add_argument("--topic", type=str, default="Dios Quiere Que Veas Esto Todos Los Días", help="Video topic.")
    parser.add_argument("--text", type=str, default=None, help="Custom bold overlay text.")
    parser.add_argument("--bg", type=str, default=None, help="Path to background image.")
    parser.add_argument("--output", type=str, default=None, help="Output image path.")
    parser.add_argument("--badge", type=str, default="DR MARIO", help="Badge text.")
    args = parser.parse_args()

    out_file = generate_thumbnail(
        topic=args.topic,
        output_path=args.output,
        background_image_path=args.bg,
        overlay_text=args.text,
        badge_text=args.badge,
    )
    print(f"✅ Thumbnail successfully generated: {out_file}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_hd_thumb.py — Full HD (1920x1080) High-CTR Thumbnail Regenerator for Hábitos de Acero (Dr Mario).

Keeps the authentic Dr Mario portrait from any winning competitor thumbnail,
rebuilds a clean studio gradient on the text side, renders razor-sharp
Montserrat-ExtraBold 3D hook typography, and stamps the DR MARIO authority badge.

Usage:
    python generate_hd_thumb.py --src path/to/orig_thumb.jpg --lines "RELÁJATE..." "Y TODO" "LLEGA" --colors white white yellow --side left --out assets/thumbnails/<VID_ID>_thumb.jpg
"""

import os
import sys
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_EXTRABOLD = os.path.join(BASE_DIR, "assets", "Montserrat-ExtraBold.ttf")

COLOR_MAP = {
    "white": (255, 255, 255, 255),
    "yellow": (255, 224, 38, 255),
    "gold": (255, 214, 48, 255),
    "red": (242, 24, 28, 255),
}


def draw_mic_icon(draw, cx, cy, size=22, color=(212, 24, 32, 255)):
    """Draws a crisp podcast studio microphone icon."""
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


def draw_clean_headline(draw, pos, text, font, fill, contour_px=3, contour_color=(12, 14, 20, 240), shadow_offset=(6, 8)):
    """Renders crisp headline typography with directional drop shadow and dark contour."""
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


def _build_studio_bg(W: int, H: int, theme: str = "obsidian") -> Image.Image:
    """Creates a clean vertical studio gradient backdrop."""
    y_coords = np.linspace(0, 1, H)
    stops_y = np.array([0.0, 0.30, 0.65, 1.0])
    if theme == "crimson":
        stops_r = np.array([115, 72, 38, 18])
        stops_g = np.array([18, 12, 8, 6])
        stops_b = np.array([22, 16, 12, 10])
    else:  # dark obsidian charcoal matching Hábitos de Acero
        stops_r = np.array([42, 28, 18, 10])
        stops_g = np.array([46, 30, 20, 12])
        stops_b = np.array([56, 38, 26, 16])

    grad_r = np.interp(y_coords, stops_y, stops_r).astype(np.uint8)
    grad_g = np.interp(y_coords, stops_y, stops_g).astype(np.uint8)
    grad_b = np.interp(y_coords, stops_y, stops_b).astype(np.uint8)

    grad_col = np.stack([grad_r, grad_g, grad_b], axis=1)
    grad_arr = np.broadcast_to(grad_col[:, None, :], (H, W, 3)).copy()
    return Image.fromarray(grad_arr, mode="RGB").convert("RGBA")


def create_hd_recreation(
    src_thumb_path: str,
    lines: list,
    line_colors: list,
    output_path: str,
    portrait_side: str = "left",
    badge_text: str = "DR MARIO",
    theme: str = "obsidian",
    highlight_line_idx: int = -1,
):
    """Regenerates a 1920x1080 HD thumbnail keeping the speaker portrait and rebuilding crisp text + badge."""
    W, H = 1920, 1080
    src = Image.open(src_thumb_path).convert("RGB")
    src_hd = src.resize((W, H), Image.Resampling.LANCZOS)
    src_hd = ImageEnhance.Sharpness(src_hd).enhance(1.25)
    src_hd = ImageEnhance.Contrast(src_hd).enhance(1.05)
    src_hd = ImageEnhance.Color(src_hd).enhance(1.04)

    canvas_bg = _build_studio_bg(W, H, theme=theme)
    mask_x = np.linspace(0, W - 1, W)

    if portrait_side == "right":
        alpha_x = np.clip((mask_x - 1080.0) / (1220.0 - 1080.0), 0.0, 1.0)
        text_center_x = 580
    else:
        alpha_x = np.clip((840.0 - mask_x) / (840.0 - 700.0), 0.0, 1.0)
        text_center_x = 1350

    alpha_x = 0.5 - 0.5 * np.cos(np.pi * alpha_x)
    alpha_2d = (np.broadcast_to(alpha_x[None, :], (H, W)) * 255).astype(np.uint8)
    portrait_mask = Image.fromarray(alpha_2d, mode="L")
    composed = Image.composite(src_hd.convert("RGBA"), canvas_bg, portrait_mask)

    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Auto-fit headline font size to keep lines inside text column
    max_col_w = 960
    font_size = 132 if len(lines) <= 3 else 112
    while font_size > 68:
        test_font = ImageFont.truetype(FONT_EXTRABOLD, font_size)
        widest = max((draw.textbbox((0, 0), t.upper(), font=test_font)[2] for t in lines), default=0)
        if widest <= max_col_w:
            break
        font_size -= 6

    font_main = ImageFont.truetype(FONT_EXTRABOLD, font_size)
    line_step = int(font_size * 1.24)
    total_text_h = line_step * len(lines)
    y_start = max(110, (H - 180 - total_text_h) // 2)

    for idx, raw_text in enumerate(lines):
        t = raw_text.strip().upper()
        cname = line_colors[idx] if idx < len(line_colors) else "white"
        fill = COLOR_MAP.get(cname.lower(), COLOR_MAP["white"])
        bbox = draw.textbbox((0, 0), t, font=font_main)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        x_pos = text_center_x - lw // 2 - bbox[0]
        y_pos = y_start + idx * line_step

        if idx == highlight_line_idx:
            pad_x, pad_y = 26, 14
            draw.rounded_rectangle(
                [x_pos + bbox[0] - pad_x, y_pos + bbox[1] - pad_y, x_pos + bbox[2] + pad_x, y_pos + bbox[3] + pad_y],
                radius=16,
                fill=(215, 22, 28, 245),
            )
            fill = COLOR_MAP["white"]

        draw_clean_headline(draw, (x_pos, y_pos), t, font=font_main, fill=fill, contour_px=4, shadow_offset=(6, 8))

    # DR MARIO Authority Pill Badge
    font_badge = ImageFont.truetype(FONT_EXTRABOLD, 38)
    b_text = badge_text.strip().upper()
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

    shadow_pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_pill).rounded_rectangle([px0 + 4, py0 + 8, px1 + 4, py1 + 8], radius=pill_h // 2, fill=(0, 0, 0, 175))
    shadow_pill = shadow_pill.filter(ImageFilter.GaussianBlur(radius=6))
    composed = Image.alpha_composite(composed, shadow_pill)

    draw.rounded_rectangle([px0, py0, px1, py1], radius=pill_h // 2, fill=(212, 22, 30, 255), outline=(255, 224, 64, 240), width=3)
    mic_cx = px0 + pad_left + 27
    mic_cy = (py0 + py1) // 2
    draw.ellipse([mic_cx - 27, mic_cy - 27, mic_cx + 27, mic_cy + 27], fill=(255, 255, 255, 255))
    draw_mic_icon(draw, mic_cx, mic_cy, size=24, color=(212, 22, 30, 255))

    tx = px0 + pad_left + mic_area_w + 4
    ty = py0 + (pill_h - th) // 2 - tbbox[1]
    draw.text((tx + 2, ty + 2), b_text, font=font_badge, fill=(75, 0, 0, 190))
    draw.text((tx, ty), b_text, font=font_badge, fill=(255, 255, 255, 255))

    final = Image.alpha_composite(composed, txt_layer).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.save(output_path, "JPEG", quality=96, subsampling=0)
    print(f"✅ Created Full HD thumbnail: {output_path} ({final.size[0]}x{final.size[1]}, {os.path.getsize(output_path)/1024:.1f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Regenerate high-CTR 1920x1080 thumbnail for Hábitos de Acero.")
    parser.add_argument("--src", required=True, help="Source reference thumbnail image path")
    parser.add_argument("--lines", nargs="+", required=True, help="Headline lines (2-4 lines)")
    parser.add_argument("--colors", nargs="+", default=["yellow", "white", "yellow"], help="Line colors: white, yellow, gold, red")
    parser.add_argument("--side", choices=["left", "right"], default="left", help="Side where Dr Mario portrait appears")
    parser.add_argument("--theme", choices=["obsidian", "crimson"], default="obsidian", help="Background gradient theme")
    parser.add_argument("--highlight", type=int, default=-1, help="0-based index of line to highlight in a red box")
    parser.add_argument("--badge", default="DR MARIO", help="Speaker badge text")
    parser.add_argument("--out", required=True, help="Output JPEG path")
    args = parser.parse_args()

    create_hd_recreation(
        src_thumb_path=args.src,
        lines=args.lines,
        line_colors=args.colors,
        output_path=args.out,
        portrait_side=args.side,
        badge_text=args.badge,
        theme=args.theme,
        highlight_line_idx=args.highlight,
    )


if __name__ == "__main__":
    main()

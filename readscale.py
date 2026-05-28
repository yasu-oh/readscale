#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from PIL import (
    Image,
    ImageChops,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)


PRESETS: dict[str, dict[str, float | int]] = {
    "flyer": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.08,
        "color": 1.02,
        "sharp_radius": 0.72,
        "sharp_percent": 125,
        "sharp_threshold": 2,
        "edge_blur": 0.55,
        "edge_gain": 1.75,
        "edge_gamma": 0.85,
        "autocontrast_cutoff": 0.04,
        "jpeg_noise_reduce": 0,
    },
    "text": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.14,
        "color": 1.00,
        "sharp_radius": 0.60,
        "sharp_percent": 165,
        "sharp_threshold": 1,
        "edge_blur": 0.35,
        "edge_gain": 2.20,
        "edge_gamma": 0.72,
        "autocontrast_cutoff": 0.06,
        "jpeg_noise_reduce": 0,
    },
    "soft": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.04,
        "color": 1.02,
        "sharp_radius": 0.85,
        "sharp_percent": 85,
        "sharp_threshold": 3,
        "edge_blur": 0.75,
        "edge_gain": 1.35,
        "edge_gamma": 1.00,
        "autocontrast_cutoff": 0.025,
        "jpeg_noise_reduce": 0,
    },
    "clean": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.06,
        "color": 1.01,
        "sharp_radius": 0.75,
        "sharp_percent": 105,
        "sharp_threshold": 3,
        "edge_blur": 0.70,
        "edge_gain": 1.55,
        "edge_gamma": 0.95,
        "autocontrast_cutoff": 0.035,
        "jpeg_noise_reduce": 1,
    },
}


RESAMPLING_FILTERS = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "nearest": Image.Resampling.NEAREST,
}


SUPPORTED_OUTPUT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def ensure_rgb_or_rgba(img: Image.Image) -> Image.Image:
    """Normalize image mode while preserving alpha when present."""
    if img.mode in ("RGB", "RGBA"):
        return img

    has_alpha = (
        img.mode in ("LA", "PA")
        or (img.mode == "P" and "transparency" in img.info)
        or "A" in img.getbands()
    )

    return img.convert("RGBA" if has_alpha else "RGB")


def get_output_size(img: Image.Image, scale: float) -> tuple[int, int]:
    if scale <= 0:
        raise ValueError("--scale must be greater than 0")

    width = max(1, round(img.width * scale))
    height = max(1, round(img.height * scale))

    return width, height


def resize_by_scale(
    img: Image.Image,
    scale: float,
    resample: str = "lanczos",
) -> Image.Image:
    if resample not in RESAMPLING_FILTERS:
        raise ValueError(f"Unknown resampling filter: {resample}")

    width, height = get_output_size(img, scale)

    return img.resize(
        (width, height),
        RESAMPLING_FILTERS[resample],
    )


def apply_gamma(mask: Image.Image, gamma: float) -> Image.Image:
    if gamma <= 0:
        raise ValueError("gamma must be greater than 0")

    if abs(gamma - 1.0) < 1e-6:
        return mask

    lut = [
        min(255, max(0, round(((i / 255.0) ** gamma) * 255)))
        for i in range(256)
    ]

    return mask.point(lut)


def make_edge_mask_from_luma(
    luma: Image.Image,
    blur: float,
    gain: float,
    gamma: float,
) -> Image.Image:
    """
    Build a text/line-oriented edge mask from luminance.

    A morphological gradient is used instead of FIND_EDGES.
    This tends to be less harsh on flyer backgrounds and JPEG noise.
    """
    base = luma.convert("L")

    local_max = base.filter(ImageFilter.MaxFilter(3))
    local_min = base.filter(ImageFilter.MinFilter(3))
    edges = ImageChops.difference(local_max, local_min)

    edges = ImageOps.autocontrast(edges)

    if blur > 0:
        edges = edges.filter(ImageFilter.GaussianBlur(blur))

    if gain != 1.0:
        edges = ImageEnhance.Contrast(edges).enhance(gain)

    edges = apply_gamma(edges, gamma)

    return edges


def split_alpha(img: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    if img.mode == "RGBA":
        return img.convert("RGB"), img.getchannel("A")

    if img.mode != "RGB":
        return img.convert("RGB"), None

    return img, None


def merge_alpha(rgb: Image.Image, alpha: Image.Image | None) -> Image.Image:
    if alpha is None:
        return rgb

    out = rgb.convert("RGBA")
    out.putalpha(alpha)

    return out


def enhance_for_readability(
    img: Image.Image,
    preset: str = "flyer",
    autocontrast: bool = True,
    edge_sharpen: bool = True,
) -> Image.Image:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    p = PRESETS[preset]

    rgb, alpha = split_alpha(img)

    if int(p["jpeg_noise_reduce"]) > 0:
        rgb = rgb.filter(ImageFilter.MedianFilter(3))

    ycbcr = rgb.convert("YCbCr")
    y, cb, cr = ycbcr.split()

    if autocontrast:
        y = ImageOps.autocontrast(
            y,
            cutoff=float(p["autocontrast_cutoff"]),
        )

    y = ImageEnhance.Brightness(y).enhance(float(p["luma_brightness"]))
    y = ImageEnhance.Contrast(y).enhance(float(p["luma_contrast"]))

    if edge_sharpen:
        edge_mask = make_edge_mask_from_luma(
            y,
            blur=float(p["edge_blur"]),
            gain=float(p["edge_gain"]),
            gamma=float(p["edge_gamma"]),
        )

        y_sharp = y.filter(
            ImageFilter.UnsharpMask(
                radius=float(p["sharp_radius"]),
                percent=int(p["sharp_percent"]),
                threshold=int(p["sharp_threshold"]),
            )
        )

        y = Image.composite(y_sharp, y, edge_mask)
    else:
        y = y.filter(
            ImageFilter.UnsharpMask(
                radius=float(p["sharp_radius"]),
                percent=int(p["sharp_percent"]),
                threshold=int(p["sharp_threshold"]),
            )
        )

    out = Image.merge("YCbCr", (y, cb, cr)).convert("RGB")
    out = ImageEnhance.Color(out).enhance(float(p["color"]))

    return merge_alpha(out, alpha)


def validate_output_path(output_path: Path) -> None:
    suffix = output_path.suffix.lower()

    if suffix not in SUPPORTED_OUTPUT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_EXTENSIONS))
        raise ValueError(
            f"Unsupported output extension: {suffix}. "
            f"Supported: {supported}"
        )


def save_image(
    img: Image.Image,
    output_path: Path,
    quality: int = 95,
    dpi: tuple[int, int] | None = None,
) -> None:
    validate_output_path(output_path)

    suffix = output_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs: dict[str, Any] = {}

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    if suffix in [".jpg", ".jpeg"]:
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.getchannel("A"))
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img.save(
            output_path,
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=0,
            **save_kwargs,
        )

    elif suffix == ".png":
        img.save(
            output_path,
            optimize=True,
            compress_level=9,
            **save_kwargs,
        )

    elif suffix == ".webp":
        img.save(
            output_path,
            quality=quality,
            method=6,
            **save_kwargs,
        )

    else:
        img.save(output_path, **save_kwargs)


def readscale_image(
    input_path: str,
    output_path: str,
    scale: float = 3.0,
    preset: str = "flyer",
    autocontrast: bool = True,
    edge_sharpen: bool = True,
    quality: int = 95,
    resample: str = "lanczos",
    keep_dpi: bool = True,
) -> None:
    input_path_obj = Path(input_path)
    output_path_obj = Path(output_path)

    if not input_path_obj.exists():
        raise FileNotFoundError(f"Input file not found: {input_path_obj}")

    validate_output_path(output_path_obj)

    with Image.open(input_path_obj) as img:
        img = ImageOps.exif_transpose(img)
        img = ensure_rgb_or_rgba(img)

        original_size = img.size
        original_dpi = img.info.get("dpi") if keep_dpi else None

        resized = resize_by_scale(
            img,
            scale=scale,
            resample=resample,
        )

        enhanced = enhance_for_readability(
            resized,
            preset=preset,
            autocontrast=autocontrast,
            edge_sharpen=edge_sharpen,
        )

        save_image(
            enhanced,
            output_path_obj,
            quality=quality,
            dpi=original_dpi,
        )

    with Image.open(output_path_obj) as check:
        output_size = check.size

    print(f"Saved        : {output_path_obj}")
    print(f"Original size: {original_size[0]} x {original_size[1]} px")
    print(f"Output size  : {output_size[0]} x {output_size[1]} px")
    print(f"Scale        : {scale}x")
    print(f"Preset       : {preset}")
    print(f"Resample     : {resample}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upscale flyer/text images by scale with readability enhancement."
    )

    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")

    parser.add_argument(
        "--scale",
        type=float,
        default=3.0,
        help="Upscale factor. Default: 3.0",
    )

    parser.add_argument(
        "--preset",
        choices=PRESETS.keys(),
        default="flyer",
        help="Enhancement preset. Default: flyer",
    )

    parser.add_argument(
        "--resample",
        choices=RESAMPLING_FILTERS.keys(),
        default="lanczos",
        help="Resampling filter. Default: lanczos",
    )

    parser.add_argument(
        "--no-autocontrast",
        action="store_true",
        help="Disable slight autocontrast",
    )

    parser.add_argument(
        "--no-edge-sharpen",
        action="store_true",
        help="Disable edge-aware sharpening",
    )

    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG/WebP quality. Default: 95",
    )

    parser.add_argument(
        "--no-keep-dpi",
        action="store_true",
        help="Do not preserve input DPI metadata when possible",
    )

    args = parser.parse_args()

    readscale_image(
        input_path=args.input,
        output_path=args.output,
        scale=args.scale,
        preset=args.preset,
        autocontrast=not args.no_autocontrast,
        edge_sharpen=not args.no_edge_sharpen,
        quality=args.quality,
        resample=args.resample,
        keep_dpi=not args.no_keep_dpi,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
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
        "luma_contrast": 1.07,
        "tone_curve": 0.14,
        "local_contrast_radius": 1.25,
        "local_contrast_percent": 24,
        "local_contrast_threshold": 5,
        "color": 1.02,
        "sharp_radius": 0.68,
        "sharp_percent": 118,
        "sharp_threshold": 2,
        "edge_blur": 0.55,
        "edge_gain": 1.65,
        "edge_gamma": 0.88,
        "edge_autocontrast_cutoff": 0.07,
        "edge_small_weight": 0.74,
        "edge_threshold": 18,
        "edge_expand": 3,
        "edge_broad_suppression": 0.22,
        "autocontrast_cutoff": 0.035,
        "jpeg_noise_reduce": 0,
    },
    "text": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.16,
        "tone_curve": 0.28,
        "local_contrast_radius": 0.95,
        "local_contrast_percent": 32,
        "local_contrast_threshold": 4,
        "color": 1.00,
        "sharp_radius": 0.55,
        "sharp_percent": 170,
        "sharp_threshold": 1,
        "edge_blur": 0.30,
        "edge_gain": 2.25,
        "edge_gamma": 0.70,
        "edge_autocontrast_cutoff": 0.10,
        "edge_small_weight": 0.88,
        "edge_threshold": 14,
        "edge_expand": 3,
        "edge_broad_suppression": 0.20,
        "autocontrast_cutoff": 0.055,
        "jpeg_noise_reduce": 0,
    },
    "soft": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.03,
        "tone_curve": 0.05,
        "local_contrast_radius": 1.75,
        "local_contrast_percent": 10,
        "local_contrast_threshold": 8,
        "color": 1.01,
        "sharp_radius": 0.90,
        "sharp_percent": 65,
        "sharp_threshold": 4,
        "edge_blur": 0.85,
        "edge_gain": 1.18,
        "edge_gamma": 1.08,
        "edge_autocontrast_cutoff": 0.03,
        "edge_small_weight": 0.55,
        "edge_threshold": 28,
        "edge_expand": 3,
        "edge_broad_suppression": 0.38,
        "autocontrast_cutoff": 0.02,
        "jpeg_noise_reduce": 0,
    },
    "clean": {
        "luma_brightness": 1.00,
        "luma_contrast": 1.05,
        "tone_curve": 0.14,
        "local_contrast_radius": 1.45,
        "local_contrast_percent": 14,
        "local_contrast_threshold": 8,
        "color": 1.00,
        "sharp_radius": 0.70,
        "sharp_percent": 90,
        "sharp_threshold": 4,
        "edge_blur": 0.80,
        "edge_gain": 1.40,
        "edge_gamma": 1.02,
        "edge_autocontrast_cutoff": 0.08,
        "edge_small_weight": 0.68,
        "edge_threshold": 26,
        "edge_expand": 3,
        "edge_broad_suppression": 0.36,
        "autocontrast_cutoff": 0.03,
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


@dataclass(frozen=True)
class ReadscaleResult:
    input_path: Path
    output_path: Path
    original_size: tuple[int, int]
    output_size: tuple[int, int]
    scale: float
    preset: str
    resample: str
    tone_curve: bool
    local_contrast: bool


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


def apply_s_curve(luma: Image.Image, strength: float) -> Image.Image:
    """Apply a gentle luminance S-curve for better text/background separation."""
    if strength < 0 or strength > 1:
        raise ValueError("tone curve strength must be between 0 and 1")

    if strength <= 0:
        return luma

    lut = []
    for i in range(256):
        x = i / 255.0
        smooth = x * x * (3.0 - 2.0 * x)
        y = (x * (1.0 - strength)) + (smooth * strength)
        lut.append(min(255, max(0, round(y * 255))))

    return luma.point(lut)


def apply_local_contrast(
    luma: Image.Image,
    radius: float,
    percent: int,
    threshold: int,
) -> Image.Image:
    """Lift small text and line details without globally sharpening the image."""
    if percent <= 0:
        return luma

    if radius <= 0:
        raise ValueError("local contrast radius must be greater than 0")

    return luma.filter(
        ImageFilter.UnsharpMask(
            radius=radius,
            percent=percent,
            threshold=threshold,
        )
    )


def make_edge_mask_from_luma(
    luma: Image.Image,
    blur: float,
    gain: float,
    gamma: float,
    autocontrast_cutoff: float,
    small_weight: float,
    threshold: int,
    expand: int,
    broad_suppression: float,
) -> Image.Image:
    """
    Build a text/line-oriented mask from luminance.

    Small and medium morphological gradients are blended so thin text
    strokes get priority over broad photo/illustration boundaries.
    """
    if small_weight < 0 or small_weight > 1:
        raise ValueError("small edge weight must be between 0 and 1")

    if threshold < 0 or threshold > 255:
        raise ValueError("edge threshold must be between 0 and 255")

    if expand < 1 or expand % 2 == 0:
        raise ValueError("edge expand must be a positive odd integer")

    if broad_suppression < 0 or broad_suppression > 1:
        raise ValueError("broad edge suppression must be between 0 and 1")

    base = luma.convert("L")

    small_edges = ImageChops.difference(
        base.filter(ImageFilter.MaxFilter(3)),
        base.filter(ImageFilter.MinFilter(3)),
    )
    medium_edges = ImageChops.difference(
        base.filter(ImageFilter.MaxFilter(5)),
        base.filter(ImageFilter.MinFilter(5)),
    )

    edges = Image.blend(medium_edges, small_edges, small_weight)
    edges = ImageOps.autocontrast(edges, cutoff=autocontrast_cutoff)

    if threshold > 0:
        scale = 255 / (255 - threshold)
        edges = edges.point(
            lambda v: 0 if v <= threshold else min(255, round((v - threshold) * scale))
        )

    if broad_suppression > 0:
        broad_edges = ImageChops.difference(
            base.filter(ImageFilter.MaxFilter(9)),
            base.filter(ImageFilter.MinFilter(9)),
        )
        broad_excess = ImageChops.subtract(broad_edges, small_edges)
        broad_excess = broad_excess.filter(ImageFilter.GaussianBlur(1.0))
        penalty = broad_excess.point(lambda v: round(v * broad_suppression))
        edges = ImageChops.subtract(edges, penalty)

    if expand > 1:
        edges = edges.filter(ImageFilter.MaxFilter(expand))

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
    tone_curve: bool = True,
    local_contrast: bool = True,
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

    if tone_curve:
        y = apply_s_curve(y, float(p["tone_curve"]))

    if local_contrast:
        y = apply_local_contrast(
            y,
            radius=float(p["local_contrast_radius"]),
            percent=int(p["local_contrast_percent"]),
            threshold=int(p["local_contrast_threshold"]),
        )

    if edge_sharpen:
        edge_mask = make_edge_mask_from_luma(
            y,
            blur=float(p["edge_blur"]),
            gain=float(p["edge_gain"]),
            gamma=float(p["edge_gamma"]),
            autocontrast_cutoff=float(p["edge_autocontrast_cutoff"]),
            small_weight=float(p["edge_small_weight"]),
            threshold=int(p["edge_threshold"]),
            expand=int(p["edge_expand"]),
            broad_suppression=float(p["edge_broad_suppression"]),
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


def make_default_output_path(input_path: Path) -> Path:
    return input_path.with_name(
        f"{input_path.stem}_readscale{input_path.suffix}"
    )


def readscale_image(
    input_path: str,
    output_path: str | None = None,
    scale: float = 3.0,
    preset: str = "flyer",
    autocontrast: bool = True,
    tone_curve: bool = True,
    local_contrast: bool = True,
    edge_sharpen: bool = True,
    quality: int = 95,
    resample: str = "lanczos",
    keep_dpi: bool = True,
    show_summary: bool = True,
) -> ReadscaleResult:
    input_path_obj = Path(input_path)

    if output_path is None:
        output_path_obj = make_default_output_path(input_path_obj)
    else:
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
            tone_curve=tone_curve,
            local_contrast=local_contrast,
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

    result = ReadscaleResult(
        input_path=input_path_obj,
        output_path=output_path_obj,
        original_size=original_size,
        output_size=output_size,
        scale=scale,
        preset=preset,
        resample=resample,
        tone_curve=tone_curve,
        local_contrast=local_contrast,
    )

    if show_summary:
        print_result_summary(result)

    return result


def print_result_summary(result: ReadscaleResult) -> None:
    print(f"====================================")
    print(f"Saved : {result.output_path}")
    print(f"Original size: {result.original_size[0]} x {result.original_size[1]} px")
    print(f"Output size : {result.output_size[0]} x {result.output_size[1]} px")
    print(f"Scale : {result.scale}x")
    print(f"Preset : {result.preset}")
    print(f"Resample : {result.resample}")
    print(f"Tone curve : {'on' if result.tone_curve else 'off'}")
    print(f"Local contrast : {'on' if result.local_contrast else 'off'}")


def get_worker_count(total_files: int) -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, min(total_files, cpu_count))


def print_progress(
    completed: int,
    total: int,
    message: str,
) -> None:
    percent = (completed / total) * 100
    print(f"[{percent:6.2f}%] {completed}/{total} {message}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upscale flyer/text images by scale with readability enhancement."
    )
    parser.add_argument("input", help="Input image path or directory")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output image path or directory. Default: <input_filename>_readscale.<ext> or <input_dir>_readscale/",
    )
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
        "--no-tone-curve",
        action="store_true",
        help="Disable readability-oriented luminance tone curve",
    )
    parser.add_argument(
        "--no-local-contrast",
        action="store_true",
        help="Disable local contrast enhancement for small text and lines",
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

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path not found: {input_path}")
        exit(1)

    if input_path.is_dir():
        # Directory mode
        output_dir = Path(args.output) if args.output else input_path.with_name(f"{input_path.name}_readscale")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all supported images
        files = sorted(
            [
                f
                for f in input_path.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_OUTPUT_EXTENSIONS
            ],
            key=lambda f: f.name.lower(),
        )
        if not files:
            print(f"No supported images found in {input_path}")
            return

        total = len(files)
        worker_count = get_worker_count(total)
        print(
            f"Processing {total} images from {input_path} to {output_dir} "
            f"with {worker_count} worker(s)..."
        )

        failed = 0
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            future_to_file = {
                executor.submit(
                    readscale_image,
                    input_path=str(f),
                    output_path=str(output_dir / f.name),
                    scale=args.scale,
                    preset=args.preset,
                    autocontrast=not args.no_autocontrast,
                    tone_curve=not args.no_tone_curve,
                    local_contrast=not args.no_local_contrast,
                    edge_sharpen=not args.no_edge_sharpen,
                    quality=args.quality,
                    resample=args.resample,
                    keep_dpi=not args.no_keep_dpi,
                    show_summary=False,
                ): f
                for f in files
            }

            completed = 0
            for future in as_completed(future_to_file):
                source = future_to_file[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as e:
                    failed += 1
                    print_progress(
                        completed,
                        total,
                        f"Failed: {source.name}: {e}",
                    )
                else:
                    print_progress(
                        completed,
                        total,
                        (
                            f"Saved: {result.output_path} "
                            f"({result.original_size[0]}x{result.original_size[1]} "
                            f"-> {result.output_size[0]}x{result.output_size[1]} px)"
                        ),
                    )

        if failed:
            print(f"Done. {total - failed} succeeded, {failed} failed.")
        else:
            print("Done.")
    else:
        # File mode
        readscale_image(
            input_path=args.input,
            output_path=args.output,
            scale=args.scale,
            preset=args.preset,
            autocontrast=not args.no_autocontrast,
            tone_curve=not args.no_tone_curve,
            local_contrast=not args.no_local_contrast,
            edge_sharpen=not args.no_edge_sharpen,
            quality=args.quality,
            resample=args.resample,
            keep_dpi=not args.no_keep_dpi,
        )


if __name__ == "__main__":
    main()

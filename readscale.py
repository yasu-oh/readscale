#!/usr/bin/env python3
from pathlib import Path
from PIL import (
    Image,
    ImageOps,
    ImageFilter,
    ImageEnhance,
)
import argparse


PRESETS = {
    "flyer": {
        "contrast": 1.06,
        "color": 1.03,
        "brightness": 1.00,
        "sharp_radius": 0.75,
        "sharp_percent": 115,
        "sharp_threshold": 2,
        "edge_blur": 0.7,
        "edge_gain": 1.8,
        "autocontrast_cutoff": 0.05,
    },
    "text": {
        "contrast": 1.10,
        "color": 1.00,
        "brightness": 1.00,
        "sharp_radius": 0.65,
        "sharp_percent": 145,
        "sharp_threshold": 1,
        "edge_blur": 0.5,
        "edge_gain": 2.2,
        "autocontrast_cutoff": 0.08,
    },
    "soft": {
        "contrast": 1.03,
        "color": 1.02,
        "brightness": 1.00,
        "sharp_radius": 0.9,
        "sharp_percent": 80,
        "sharp_threshold": 3,
        "edge_blur": 0.9,
        "edge_gain": 1.3,
        "autocontrast_cutoff": 0.03,
    },
}


def ensure_rgb_or_rgba(img: Image.Image) -> Image.Image:
    if img.mode in ("RGB", "RGBA"):
        return img

    has_alpha = (
        img.mode in ("LA", "PA")
        or (img.mode == "P" and "transparency" in img.info)
        or "A" in img.getbands()
    )

    return img.convert("RGBA" if has_alpha else "RGB")


def resize_by_scale(img: Image.Image, scale: float) -> Image.Image:
    if scale <= 0:
        raise ValueError("--scale must be greater than 0")

    width = max(1, round(img.width * scale))
    height = max(1, round(img.height * scale))

    return img.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


def autocontrast_preserve_tone(img: Image.Image, cutoff: float) -> Image.Image:
    try:
        return ImageOps.autocontrast(
            img,
            cutoff=cutoff,
            preserve_tone=True,
        )
    except TypeError:
        return ImageOps.autocontrast(
            img,
            cutoff=cutoff,
        )


def make_edge_mask(
    img: Image.Image,
    blur: float,
    gain: float,
) -> Image.Image:
    gray = img.convert("L")

    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges)

    if blur > 0:
        edges = edges.filter(ImageFilter.GaussianBlur(blur))

    if gain != 1.0:
        edges = ImageEnhance.Contrast(edges).enhance(gain)

    return edges


def enhance_for_readability(
    img: Image.Image,
    preset: str = "flyer",
    autocontrast: bool = True,
    edge_sharpen: bool = True,
) -> Image.Image:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    p = PRESETS[preset]

    out = img

    alpha = None
    if out.mode == "RGBA":
        alpha = out.getchannel("A")
        out = out.convert("RGB")

    if autocontrast:
        out = autocontrast_preserve_tone(
            out,
            cutoff=p["autocontrast_cutoff"],
        )

    out = ImageEnhance.Brightness(out).enhance(p["brightness"])
    out = ImageEnhance.Contrast(out).enhance(p["contrast"])
    out = ImageEnhance.Color(out).enhance(p["color"])

    if edge_sharpen:
        edge_mask = make_edge_mask(
            out,
            blur=p["edge_blur"],
            gain=p["edge_gain"],
        )

        sharpened = out.filter(
            ImageFilter.UnsharpMask(
                radius=p["sharp_radius"],
                percent=p["sharp_percent"],
                threshold=p["sharp_threshold"],
            )
        )

        out = Image.composite(sharpened, out, edge_mask)
    else:
        out = out.filter(
            ImageFilter.UnsharpMask(
                radius=p["sharp_radius"],
                percent=p["sharp_percent"],
                threshold=p["sharp_threshold"],
            )
        )

    if alpha is not None:
        out.putalpha(alpha)

    return out


def save_image(img: Image.Image, output_path: Path, quality: int = 95):
    suffix = output_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
        )

    elif suffix == ".png":
        img.save(
            output_path,
            optimize=True,
            compress_level=9,
        )

    elif suffix == ".webp":
        img.save(
            output_path,
            quality=quality,
            method=6,
        )

    else:
        img.save(output_path)


def readscale_image(
    input_path: str,
    output_path: str,
    scale: float = 3.0,
    preset: str = "flyer",
    autocontrast: bool = True,
    edge_sharpen: bool = True,
    quality: int = 95,
):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        img = ensure_rgb_or_rgba(img)

        original_size = img.size

        resized = resize_by_scale(
            img,
            scale=scale,
        )

        enhanced = enhance_for_readability(
            resized,
            preset=preset,
            autocontrast=autocontrast,
            edge_sharpen=edge_sharpen,
        )

        save_image(
            enhanced,
            output_path,
            quality=quality,
        )

    with Image.open(output_path) as check:
        output_size = check.size

    print(f"Saved        : {output_path}")
    print(f"Original size: {original_size[0]} x {original_size[1]} px")
    print(f"Output size  : {output_size[0]} x {output_size[1]} px")
    print(f"Scale        : {scale}x")
    print(f"Preset       : {preset}")


def main():
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
        help="Enhancement preset",
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
        help="JPEG/WebP quality",
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
    )


if __name__ == "__main__":
    main()

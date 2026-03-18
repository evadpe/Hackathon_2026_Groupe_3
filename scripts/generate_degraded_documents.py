from pathlib import Path
import shutil
import random

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageDraw


BASE_DIR = Path(__file__).resolve().parent.parent

SOURCE_SPLITS = {
    "train": BASE_DIR / "data" / "train",
    "val": BASE_DIR / "data" / "val",
    "test": BASE_DIR / "data" / "test",
}

OUTPUT_ROOT = BASE_DIR / "data" / "degraded"


try:
    RESAMPLE_NEAREST = Image.Resampling.NEAREST
    RESAMPLE_BILINEAR = Image.Resampling.BILINEAR
except AttributeError:
    RESAMPLE_NEAREST = Image.NEAREST
    RESAMPLE_BILINEAR = Image.BILINEAR


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def render_pdf_first_page(pdf_path: Path, zoom: float = 2.0) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return image
    finally:
        doc.close()


def add_blur(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=2))


def add_pixelization(image: Image.Image) -> Image.Image:
    width, height = image.size
    small = image.resize((max(1, width // 6), max(1, height // 6)), RESAMPLE_BILINEAR)
    return small.resize((width, height), RESAMPLE_NEAREST)


def add_rotation(image: Image.Image) -> Image.Image:
    angle = random.uniform(-4, 4)
    return image.rotate(angle, expand=True, fillcolor="white")


def add_ink_stain(image: Image.Image) -> Image.Image:
    img = image.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size

    for _ in range(random.randint(3, 6)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(20, 70)
        color = (20, 20, 20, random.randint(80, 140))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    return img.convert("RGB")


def add_masked_zone(image: Image.Image) -> Image.Image:
    img = image.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size

    # Zones approximatives importantes dans vos documents
    zones = [
        # zone numéro / date
        (40, 70, 260, 140),

        # zone fournisseur gauche
        (40, 170, 260, 290),

        # zone fournisseur droite / client
        (300, 170, 540, 290),

        # zone ligne produit
        (40, 340, 540, 390),

        # zone totaux bas droite
        (300, 430, 540, 510),
    ]

    x1, y1, x2, y2 = random.choice(zones)

    # petite variation aléatoire pour éviter toujours exactement le même masque
    dx = random.randint(-10, 10)
    dy = random.randint(-10, 10)

    x1 = max(0, x1 + dx)
    y1 = max(0, y1 + dy)
    x2 = min(width, x2 + dx)
    y2 = min(height, y2 + dy)

    draw.rectangle((x1, y1, x2, y2), fill=(230, 230, 230, 255))
    return img.convert("RGB")


def save_image(image: Image.Image, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    image.save(output_path, format="PNG")


def process_pdf(pdf_path: Path, destination_dir: Path) -> None:
    base_name = pdf_path.stem
    image = render_pdf_first_page(pdf_path)

    variants = {
        f"{base_name}_clean.png": image,
        f"{base_name}_blur.png": add_blur(image),
        f"{base_name}_pixelized.png": add_pixelization(image),
        f"{base_name}_rotated.png": add_rotation(image),
        f"{base_name}_ink_stain.png": add_ink_stain(image),
        f"{base_name}_masked_zone.png": add_masked_zone(image),
    }

    for filename, variant in variants.items():
        save_image(variant, destination_dir / filename)


def copy_non_pdf_files(source_dir: Path, destination_dir: Path) -> None:
    ensure_dir(destination_dir)

    for item in source_dir.iterdir():
        if item.is_file() and item.suffix.lower() != ".pdf":
            shutil.copy2(item, destination_dir / item.name)


def process_bundle_dir(source_bundle_dir: Path, destination_bundle_dir: Path) -> None:
    ensure_dir(destination_bundle_dir)

    copy_non_pdf_files(source_bundle_dir, destination_bundle_dir)

    for item in source_bundle_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".pdf":
            process_pdf(item, destination_bundle_dir)


def process_split(split_name: str, source_split_dir: Path) -> None:
    if not source_split_dir.exists():
        return

    output_split_dir = OUTPUT_ROOT / split_name
    ensure_dir(output_split_dir)

    # copier le manifest s'il existe
    manifest_file = source_split_dir / "manifest.csv"
    if manifest_file.exists():
        shutil.copy2(manifest_file, output_split_dir / "manifest.csv")

    for bundle_type in ["coherent", "incoherent"]:
        source_bundle_type_dir = source_split_dir / bundle_type
        if not source_bundle_type_dir.exists():
            continue

        output_bundle_type_dir = output_split_dir / bundle_type
        ensure_dir(output_bundle_type_dir)

        for bundle_dir in source_bundle_type_dir.iterdir():
            if bundle_dir.is_dir():
                process_bundle_dir(bundle_dir, output_bundle_type_dir / bundle_dir.name)


def main() -> None:
    ensure_dir(OUTPUT_ROOT)

    for split_name, source_split_dir in SOURCE_SPLITS.items():
        process_split(split_name, source_split_dir)

    print("Documents dégradés générés avec succès dans :")
    print(OUTPUT_ROOT)


if __name__ == "__main__":
    main()
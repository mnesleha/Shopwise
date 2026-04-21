from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from django.conf import settings
from django.core.files import File

from products.models import Product, ProductImage


WriteLine = Callable[[str], None]
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_demo_product_assets_root(assets_root: str | Path | None = None) -> Path:
    if assets_root is not None:
        return Path(assets_root)

    root = Path(settings.BASE_DIR)
    return root / "utils" / "seed" / "assets" / "products"


def get_demo_product_asset_files(
    *,
    slug: str,
    assets_root: str | Path | None = None,
) -> list[Path]:
    product_dir = get_demo_product_assets_root(assets_root) / slug
    if not product_dir.exists() or not product_dir.is_dir():
        return []

    return sorted(
        [
            path
            for path in product_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            and path.name.lower().startswith(f"{slug}-")
        ],
        key=lambda path: path.name.lower(),
    )


def purge_product_image_files(images: Iterable[ProductImage]) -> None:
    for image in images:
        if image.image:
            image.image.delete(save=False)


def sync_product_media(
    *,
    product: Product,
    asset_files: list[Path],
    write_line: WriteLine | None = None,
) -> list[ProductImage]:
    write = write_line or (lambda message: None)
    existing_images = list(product.images.all().order_by("sort_order", "id"))
    synced_images: list[ProductImage] = []

    for sort_order, asset_file in enumerate(asset_files):
        image = (
            existing_images[sort_order]
            if sort_order < len(existing_images)
            else ProductImage(product=product)
        )

        if image.pk and image.image:
            image.image.delete(save=False)

        image.product = product
        image.sort_order = sort_order
        image.alt_text = (
            product.name if sort_order == 0 else f"{product.name} image {sort_order + 1}"
        )

        with asset_file.open("rb") as source:
            image.image.save(asset_file.name, File(source), save=False)

        image.save()
        synced_images.append(image)

    for extra_image in existing_images[len(asset_files):]:
        if extra_image.image:
            extra_image.image.delete(save=False)
        extra_image.delete()

    primary_image = synced_images[0] if synced_images else None
    if product.primary_image_id != getattr(primary_image, "id", None):
        product.primary_image = primary_image
        product.save(update_fields=["primary_image"])

    if asset_files:
        write(f"Synced {len(asset_files)} media file(s) for {product.slug}")

    return synced_images
import os
import django
import shutil
from pathlib import Path
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoCoffeeSystem.settings")
django.setup()

from django.conf import settings
from inventory.models import Product

SOURCE_DIR = Path(r"C:/Users/Jonelle Angelo/Downloads/New folder (2)")
PRODUCTS_MEDIA_DIR = Path(settings.MEDIA_ROOT) / "products"

image_map = {
    "Hot_Americano": ["HOT-AME-REG", "HOT-AME-LRG", "HOT-AME-MEG"],
    "Hot_Latte": ["HOT-LAT-REG", "HOT-LAT-LRG", "HOT-LAT-MEG"],
    "Hot_Mocha": ["HOT-MOC-REG", "HOT-MOC-LRG", "HOT-MOC-MEG"],

    "Ice_Coffee": ["ICE-COF-REG", "ICE-COF-LRG", "ICE-COF-MEG"],
    "Iced_Latte": ["ICE-LAT-REG", "ICE-LAT-LRG", "ICE-LAT-MEG"],
    "Iced_Caramel_Coffee": ["ICE-CAR-REG", "ICE-CAR-LRG", "ICE-CAR-MEG"],

    "Chocolate_Milk": ["NON-CHO-REG", "NON-CHO-LRG", "NON-CHO-MEG"],
    "Vanilla_Milk": ["NON-VAN-REG", "NON-VAN-LRG", "NON-VAN-MEG"],

    "Butter_Croissant": ["PAS-CRO-PC"],
    "Chocolate_Muffin": ["PAS-MUF-PC"],
    "Banana_Bread_Slice": ["PAS-BAN-PC"],

    "Extra_Whipped_Cream": ["ADD-CRM-PC"],
    "Extra_Coffee_Shot": ["ADD-SHT-PC"],
}

def find_image(base_name):
    for ext in [".jpeg", ".jpg", ".png", ".webp"]:
        p = SOURCE_DIR / f"{base_name}{ext}"
        if p.exists():
            return p
    return None

print("SOURCE EXISTS:", SOURCE_DIR.exists())
print("SOURCE DIR:", SOURCE_DIR)

if not SOURCE_DIR.exists():
    raise SystemExit("ERROR: Source folder not found.")

PRODUCTS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

backup_dir = PRODUCTS_MEDIA_DIR.parent / f"products_backup_before_real_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if PRODUCTS_MEDIA_DIR.exists():
    shutil.copytree(PRODUCTS_MEDIA_DIR, backup_dir, dirs_exist_ok=True)
    print("BACKUP CREATED:", backup_dir)

updated = 0
missing_images = []
missing_products = []

for image_name, product_codes in image_map.items():
    src = find_image(image_name)

    if not src:
        missing_images.append(image_name)
        continue

    for code in product_codes:
        product = Product.objects.filter(product_code=code).first()

        if not product:
            missing_products.append(code)
            continue

        dest_name = f"{code.lower()}{src.suffix.lower()}"
        dest = PRODUCTS_MEDIA_DIR / dest_name

        shutil.copy2(src, dest)

        product.image = f"products/{dest_name}"
        product.save(update_fields=["image"])

        updated += 1
        print("UPDATED:", code, "->", product.image)

print("\nDONE")
print("Updated products:", updated)

if missing_images:
    print("\nMISSING IMAGE FILES:")
    for x in missing_images:
        print("-", x)

if missing_products:
    print("\nMISSING PRODUCT CODES:")
    for x in missing_products:
        print("-", x)

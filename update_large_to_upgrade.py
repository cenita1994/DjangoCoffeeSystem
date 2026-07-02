import os
import django
import shutil
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoCoffeeSystem.settings")
django.setup()

from inventory.models import Product

media_products = Path("media/products")

updates = {
    "HOT-AME-LRG": ("HOT-AME-UPG", "Hot Americano - Upgrade", "Upgrade"),
    "HOT-LAT-LRG": ("HOT-LAT-UPG", "Hot Latte - Upgrade", "Upgrade"),
    "HOT-MOC-LRG": ("HOT-MOC-UPG", "Hot Mocha - Upgrade", "Upgrade"),

    "ICE-COF-LRG": ("ICE-COF-UPG", "Iced Coffee - Upgrade", "Upgrade"),
    "ICE-LAT-LRG": ("ICE-LAT-UPG", "Iced Latte - Upgrade", "Upgrade"),
    "ICE-CAR-LRG": ("ICE-CAR-UPG", "Iced Caramel Coffee - Upgrade", "Upgrade"),

    "NON-CHO-LRG": ("NON-CHO-UPG", "Chocolate Milk - Upgrade", "Upgrade"),
    "NON-VAN-LRG": ("NON-VAN-UPG", "Vanilla Milk - Upgrade", "Upgrade"),
}

for old_code, (new_code, new_name, new_size) in updates.items():
    product = Product.objects.filter(product_code=old_code).first()

    if not product:
        product = Product.objects.filter(product_code=new_code).first()
        if product:
            product.name = new_name
            product.size = new_size
            product.image = f"products/{new_code.lower()}.jpg"
            product.save()
            print("ALREADY UPDATED:", new_code)
        else:
            print("NOT FOUND:", old_code)
        continue

    product.product_code = new_code
    product.name = new_name
    product.size = new_size
    product.description = product.description.replace("Large", "Upgrade").replace("large", "upgrade")
    product.image = f"products/{new_code.lower()}.jpg"
    product.save()

    print("UPDATED:", old_code, "->", new_code)

print("DONE")

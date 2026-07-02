from django.db import models
from django.contrib.auth.models import User


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    SIZE_CHOICES = [
        ('Regular', 'Regular'),
        ('Upgrade', 'Upgrade'),
        ('Mega', 'Mega'),
        ('Not Applicable', 'Not Applicable'),
    ]

    product_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text='Example: AMR-REG-0001'
    )

    name = models.CharField(max_length=100)

    # Old text category field.
    # Keep muna natin ito para hindi masira old data, reports, and templates.
    category = models.CharField(max_length=100, blank=True)

    # New controlled category field.
    # Ito ang gagamitin natin sa dropdown.
    product_category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='products'
    )

    size = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
        default='Not Applicable'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Product cost / puhunan per item'
    )

    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['product_category__name', 'name', 'size']

    def __str__(self):
        return self.display_name()

    def save(self, *args, **kwargs):
        # Sync dropdown category to old text category field.
        # Para gumana pa rin yung old templates/reports na gumagamit ng product.category.
        if self.product_category:
            self.category = self.product_category.name

        super().save(*args, **kwargs)

        if not self.product_code:
            self.product_code = self.generate_product_code()
            super().save(update_fields=['product_code', 'category'])

    def generate_product_code(self):
        if self.product_category:
            category_source = self.product_category.name
        elif self.category:
            category_source = self.category
        else:
            category_source = 'Product'

        category_prefix = ''.join(
            word[0] for word in category_source.split() if word
        ).upper()

        name_prefix = ''.join(
            word[0] for word in self.name.split() if word
        ).upper()

        size_prefix_map = {
            'Regular': 'REG',
            'Upgrade': 'UPG',
            'Mega': 'MEG',
            'Not Applicable': 'NA',
        }

        size_prefix = size_prefix_map.get(self.size, 'NA')

        if not category_prefix:
            category_prefix = 'PRD'

        if not name_prefix:
            name_prefix = 'ITEM'

        return f"{category_prefix}-{name_prefix}-{size_prefix}-{self.id:04d}"

    def display_name(self):
        if self.size and self.size != 'Not Applicable':
            return f"{self.name} - {self.size}"

        return self.name

    def estimated_margin(self):
        return self.price - self.cost_price

    
    def display_category(self):
        if self.product_category:
            return self.product_category.name

        if self.category:
            return self.category

        return 'Uncategorized'

    def current_stock(self):
        try:
            return self.stock.quantity
        except Stock.DoesNotExist:
            return 0

    def stock_status(self):
        try:
            if self.stock.quantity == 0:
                return "Out of Stock"
            elif self.stock.quantity <= self.stock.reorder_level:
                return "Low Stock"
            else:
                return "Available"
        except Stock.DoesNotExist:
            return "No Stock Record"

class Stock(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock'
    )
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} available"

    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.reorder_level:
            return "Low Stock"
        else:
            return "Available"


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('Stock In', 'Stock In'),
        ('Stock Out', 'Stock Out'),
        ('Adjustment', 'Adjustment'),
        ('Return', 'Return'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES
    )

    quantity = models.PositiveIntegerField()

    previous_quantity = models.PositiveIntegerField(default=0)
    new_quantity = models.PositiveIntegerField(default=0)

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Example: Order #15, Restock Delivery, Manual Adjustment'
    )

    remarks = models.TextField(blank=True, null=True)

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )

    movement_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date']

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} - {self.quantity}"
    


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Milliliters'),
        ('L', 'Liters'),
        ('pc', 'Pieces'),
        ('pack', 'Packs'),
    ]

    name = models.CharField(
        max_length=100,
        unique=True
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='pc'
    )

    current_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text='Current available ingredient quantity'
    )

    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text='Minimum quantity before restock is recommended'
    )

    safety_buffer_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
        help_text='Additional buffer percentage for weekly planning'
    )

    is_active = models.BooleanField(default=True)

    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ingredient'
        verbose_name_plural = 'Ingredients'

    def __str__(self):
        return f"{self.name} ({self.unit})"

    def stock_status(self):
        if self.current_quantity <= 0:
            return 'Out of Stock'

        if self.current_quantity <= self.reorder_level:
            return 'Low Stock'

        return 'Available'


class ProductRecipeItem(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recipe_items'
    )

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name='product_recipes'
    )

    quantity_required = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text='Ingredient quantity needed to produce one unit of this product'
    )

    is_active = models.BooleanField(default=True)

    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__name', 'ingredient__name']
        unique_together = ['product', 'ingredient']
        verbose_name = 'Product Recipe Item'
        verbose_name_plural = 'Product Recipe Items'

    def __str__(self):
        return f"{self.product.display_name()} - {self.ingredient.name}: {self.quantity_required} {self.ingredient.unit}"
    


class IngredientMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('Stock In', 'Stock In'),
        ('Stock Out', 'Stock Out'),
        ('Adjustment', 'Adjustment'),
    ]

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='movements'
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )

    previous_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    new_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Example: Delivery Receipt #001, Manual Adjustment'
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingredient_movements'
    )

    movement_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date']
        verbose_name = 'Ingredient Movement'
        verbose_name_plural = 'Ingredient Movements'

    def __str__(self):
        return f"{self.ingredient.name} - {self.movement_type} - {self.quantity} {self.ingredient.unit}"
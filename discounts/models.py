from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User

from orders.models import OrderItem


class DiscountRule(models.Model):
    DISCOUNT_CATEGORY_CHOICES = [
        ('Senior', 'Senior Citizen'),
        ('PWD', 'PWD'),
        ('Promo', 'Promo'),
        ('Manual', 'Manual Discount'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ('Percentage', 'Percentage'),
        ('Fixed Amount', 'Fixed Amount'),
        ('Buy 1 Take 1', 'Buy 1 Take 1'),
    ]

    name = models.CharField(max_length=100)

    category = models.CharField(
        max_length=20,
        choices=DISCOUNT_CATEGORY_CHOICES
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='Percentage'
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Example: 20.00 means 20%'
    )

    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    requires_id_card = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    description = models.TextField(blank=True, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def display_value(self):
        if self.discount_type == 'Percentage':
            return f'{self.percentage}%'

        if self.discount_type == 'Fixed Amount':
            return f'₱{self.fixed_amount}'

        if self.discount_type == 'Buy 1 Take 1':
            return 'Buy 1 Take 1'

        return 'N/A'


class OrderItemDiscount(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='discounts'
    )

    discount_rule = models.ForeignKey(
        DiscountRule,
        on_delete=models.PROTECT,
        related_name='order_item_discounts'
    )

    discounted_quantity = models.PositiveIntegerField(default=1)

    cardholder_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    card_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_item_discounts'
    )

    remarks = models.TextField(blank=True, null=True)

    date_applied = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_applied']

    def __str__(self):
        return f'{self.discount_rule.name} - {self.order_item.product.name} x {self.discounted_quantity}'   
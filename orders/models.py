from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from inventory.models import Product


VAT_RATE = Decimal('0.12')


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('Online', 'Online'),
        ('Walk-in', 'Walk-in'),
    ]

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ('None', 'None'),
        ('Senior', 'Senior Citizen'),
        ('PWD', 'PWD'),
        ('Promo', 'Promo'),
        ('Manual', 'Manual Discount'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('None', 'None'),
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Wallet', 'Wallet Balance'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
        ('Refunded', 'Refunded'),
    ]

    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='Walk-in'
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_orders'
    )

    customer_name = models.CharField(max_length=100, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Draft'
    )

    subtotal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='None'
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vatable_sales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vat_exempt_sales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vat_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='None'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Unpaid'
    )

    payment_reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    amount_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    change_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True
    )

    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_orders'
    )

    payment_received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_order_payments'
    )

    stock_deducted = models.BooleanField(default=False)
    ingredients_deducted = models.BooleanField(default=False)

    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.order_type}"

    def generate_receipt_number(self):
        if not self.receipt_number:
            today = timezone.now().strftime('%Y%m%d')
            self.receipt_number = f"RCPT-{today}-{self.id:06d}"

    def update_total(self):
        gross_sales = Decimal('0.00')

        total_discount = Decimal('0.00')
        senior_pwd_discount = Decimal('0.00')
        regular_discount = Decimal('0.00')

        senior_pwd_gross_sales = Decimal('0.00')
        vat_exempt_sales = Decimal('0.00')

        for item in self.items.all():
            item_price = Decimal(str(item.price))
            item_quantity = Decimal(str(item.quantity))
            item_gross = item_price * item_quantity

            gross_sales += item_gross

            for item_discount in item.discounts.all():
                discount_amount = Decimal(str(item_discount.discount_amount))
                discounted_quantity = Decimal(str(item_discount.discounted_quantity))
                discounted_gross = item_price * discounted_quantity

                total_discount += discount_amount

                if item_discount.discount_rule.category in ['Senior', 'PWD']:
                    senior_pwd_discount += discount_amount
                    senior_pwd_gross_sales += discounted_gross

                    vat_exempt_base = discounted_gross / (Decimal('1.00') + VAT_RATE)
                    vat_exempt_sales += vat_exempt_base
                else:
                    regular_discount += discount_amount

        regular_gross_sales = gross_sales - senior_pwd_gross_sales

        if regular_gross_sales < 0:
            regular_gross_sales = Decimal('0.00')

        vatable_sales = regular_gross_sales / (Decimal('1.00') + VAT_RATE)
        vat_amount = regular_gross_sales - vatable_sales

        total_amount = (regular_gross_sales - regular_discount) + vat_exempt_sales

        if total_amount < 0:
            total_amount = Decimal('0.00')

        self.subtotal_amount = money(gross_sales)
        self.discount_amount = money(total_discount)
        self.vatable_sales = money(vatable_sales)
        self.vat_exempt_sales = money(vat_exempt_sales)
        self.vat_amount = money(vat_amount)
        self.total_amount = money(total_amount)

        if senior_pwd_discount > 0 and regular_discount > 0:
            self.discount_type = 'Manual'
        elif senior_pwd_discount > 0:
            self.discount_type = 'Senior'
        elif regular_discount > 0:
            self.discount_type = 'Promo'
        else:
            self.discount_type = 'None'

        self.save()

    def display_customer(self):
        if self.order_type == 'Online' and self.customer:
            full_name = self.customer.get_full_name()
            return full_name if full_name else self.customer.username

        return self.customer_name

    def is_paid(self):
        return self.payment_status == 'Paid'

    def has_discount(self):
        return self.discount_amount > 0

    def has_receipt(self):
        return self.receipt_number is not None and self.receipt_number != ''

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def subtotal(self):
        return self.quantity * self.price

    def total_cost(self):
        return self.quantity * self.cost_price

    def total_discount(self):
        total = Decimal('0.00')

        for item_discount in self.discounts.all():
            total += Decimal(str(item_discount.discount_amount))

        return money(total)

    def net_total(self):
        subtotal = Decimal(str(self.subtotal()))
        discount = Decimal(str(self.total_discount()))
        total = subtotal - discount

        if total < 0:
            return Decimal('0.00')

        return money(total)

    def estimated_profit(self):
        net_total = Decimal(str(self.net_total()))
        total_cost = Decimal(str(self.total_cost()))
        profit = net_total - total_cost

        return money(profit)

    def __str__(self):
        return f"{self.product.display_name()} x {self.quantity}"
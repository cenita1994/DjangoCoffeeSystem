from django.db import models
from django.contrib.auth.models import User


class CustomerWallet(models.Model):
    customer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet'
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.username} Wallet - ₱{self.balance}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('Cash In', 'Cash In'),
        ('Payment', 'Payment'),
        ('Refund', 'Refund'),
        ('Adjustment', 'Adjustment'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Wallet', 'Wallet'),
        ('System', 'System'),
    ]

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wallet_transactions'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='GCash reference number or payment reference number'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    previous_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    new_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Example: Cash In, Order #15, Refund for Order #15'
    )

    remarks = models.TextField(blank=True, null=True)

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_wallet_transactions'
    )

    transaction_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.customer.username} - {self.transaction_type} - ₱{self.amount}"
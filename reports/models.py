from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User


class CashierShift(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Closed', 'Closed'),
    ]

    cashier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cashier_shifts'
    )

    opening_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    shift_start = models.DateTimeField(auto_now_add=True)

    shift_end = models.DateTimeField(
        blank=True,
        null=True
    )

    cash_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    cash_in_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    cash_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    cash_payouts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Manual cash deductions such as expenses or cash drops.'
    )

    expected_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    actual_cash_counted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    over_short_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    gcash_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    wallet_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    gcash_cash_in = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_sales_processed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    received_by_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='received_cashier_shifts'
    )

    received_at = models.DateTimeField(
        blank=True,
        null=True
    )

    manager_remarks = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Open'
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-shift_start']
        constraints = [
            models.UniqueConstraint(
                fields=['cashier'],
                condition=models.Q(status='Open'),
                name='unique_open_shift_per_cashier'
            )
        ]

    def __str__(self):
        return f"{self.cashier.username} Shift - {self.shift_start.strftime('%Y-%m-%d %H:%M')}"

    def compute_expected_cash(self):
        expected_cash = (
            Decimal(str(self.opening_cash or 0))
            + Decimal(str(self.cash_sales or 0))
            + Decimal(str(self.cash_in_received or 0))
            - Decimal(str(self.cash_refunds or 0))
            - Decimal(str(self.cash_payouts or 0))
        )

        return expected_cash

    def compute_over_short(self):
        if self.actual_cash_counted is None:
            return Decimal('0.00')

        over_short = (
            Decimal(str(self.actual_cash_counted or 0))
            - Decimal(str(self.expected_cash or 0))
        )

        return over_short

    def update_cash_computation(self):
        self.expected_cash = self.compute_expected_cash()
        self.over_short_amount = self.compute_over_short()
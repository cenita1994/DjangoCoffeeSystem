from django.contrib import admin

from .models import CustomerWallet, WalletTransaction


@admin.register(CustomerWallet)
class CustomerWalletAdmin(admin.ModelAdmin):
    list_display = [
        'customer',
        'balance',
        'last_updated',
    ]

    search_fields = [
        'customer__username',
        'customer__first_name',
        'customer__last_name',
        'customer__email',
    ]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'customer',
        'transaction_type',
        'payment_method',
        'reference_number',
        'amount',
        'previous_balance',
        'new_balance',
        'performed_by',
        'transaction_date',
    ]

    list_filter = [
        'transaction_type',
        'payment_method',
        'transaction_date',
    ]

    search_fields = [
        'customer__username',
        'reference',
        'reference_number',
        'remarks',
        'performed_by__username',
    ]
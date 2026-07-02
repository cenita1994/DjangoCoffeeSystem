from django.contrib import admin

from .models import DiscountRule, OrderItemDiscount


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'discount_type',
        'percentage',
        'fixed_amount',
        'requires_id_card',
        'is_active',
        'date_created',
    ]

    list_filter = [
        'category',
        'discount_type',
        'requires_id_card',
        'is_active',
    ]

    search_fields = [
        'name',
        'description',
    ]


@admin.register(OrderItemDiscount)
class OrderItemDiscountAdmin(admin.ModelAdmin):
    list_display = [
        'order_item',
        'discount_rule',
        'discounted_quantity',
        'discount_amount',
        'cardholder_name',
        'card_number',
        'approved_by',
        'date_applied',
    ]

    list_filter = [
        'discount_rule',
        'date_applied',
    ]

    search_fields = [
        'order_item__product__name',
        'discount_rule__name',
        'cardholder_name',
        'card_number',
        'approved_by__username',
    ]
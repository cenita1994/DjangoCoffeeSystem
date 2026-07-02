from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_type',
        'display_customer',
        'created_by',
        'status',
        'total_amount',
        'order_date',
    )
    list_filter = ('order_type', 'status', 'order_date')
    search_fields = (
        'customer_name',
        'customer__username',
        'customer__first_name',
        'customer__last_name',
        'created_by__username',
    )
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
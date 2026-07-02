from django.contrib import admin
from .models import Product, Stock


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'current_stock', 'stock_status', 'date_added')
    search_fields = ('name', 'category')
    list_filter = ('category', 'date_added')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'reorder_level', 'stock_status', 'last_updated')
    search_fields = ('product__name', 'product__category')
    list_filter = ('product__category', 'last_updated')
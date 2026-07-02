from django.urls import path

from .views import (
    reports_center,
    sales_dashboard,
    sales_period_report,
    export_sales_period_report,
    estimated_profit_report,
    export_estimated_profit_report,
    ingredient_demand_report,
    export_ingredient_demand_report,
    product_sales_report,
    export_product_sales_report,
    payment_method_report,
    export_payment_method_report,
    cashier_sales_report,
    export_cashier_sales_report,
    open_cashier_shift,
    close_cashier_shift,
    receive_cashier_shift,
    cashier_shift_detail,
    cashier_shift_list,
)


urlpatterns = [
    path('', reports_center, name='reports_center'),

    path('sales/', sales_dashboard, name='sales_dashboard'),

    path('sales-period/', sales_period_report, name='sales_period_report'),
    path('sales-period/export/', export_sales_period_report, name='sales_period_export'),

    path('estimated-profit/', estimated_profit_report, name='estimated_profit_report'),
    path('estimated-profit/export/', export_estimated_profit_report, name='estimated_profit_export'),

    path('ingredient-demand/', ingredient_demand_report, name='ingredient_demand_report'),
    path('ingredient-demand/export/', export_ingredient_demand_report, name='ingredient_demand_export'),

    path('product-sales/', product_sales_report, name='product_sales_report'),
    path('product-sales/export/', export_product_sales_report, name='product_sales_export'),

    path('payment-methods/', payment_method_report, name='payment_method_report'),
    path('payment-methods/export/', export_payment_method_report, name='payment_method_export'),

    path('cashier-sales/', cashier_sales_report, name='cashier_sales_report'),
    path('cashier-sales/export/', export_cashier_sales_report, name='cashier_sales_export'),

    path('cashier-shifts/', cashier_shift_list, name='cashier_shift_list'),
    path('cashier-shifts/open/', open_cashier_shift, name='open_cashier_shift'),
    path('cashier-shifts/<int:shift_id>/', cashier_shift_detail, name='cashier_shift_detail'),
    path('cashier-shifts/<int:shift_id>/close/', close_cashier_shift, name='close_cashier_shift'),
    path('cashier-shifts/<int:shift_id>/receive/', receive_cashier_shift, name='receive_cashier_shift'),
]
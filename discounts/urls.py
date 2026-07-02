from django.urls import path

from .views import (
    discount_rule_list,
    add_discount_rule,
    edit_discount_rule,
    delete_discount_rule,
    apply_discount_to_order_item,
    remove_discount_from_order_item,
)


urlpatterns = [
    path('', discount_rule_list, name='discount_rule_list'),
    path('add/', add_discount_rule, name='add_discount_rule'),
    path('edit/<int:id>/', edit_discount_rule, name='edit_discount_rule'),
    path('delete/<int:id>/', delete_discount_rule, name='delete_discount_rule'),

    path(
        'order-item/<int:order_item_id>/apply/',
        apply_discount_to_order_item,
        name='apply_discount_to_order_item'
    ),

    path(
        'item-discount/<int:discount_id>/remove/',
        remove_discount_from_order_item,
        name='remove_discount_from_order_item'
    ),
]
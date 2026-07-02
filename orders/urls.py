from django.urls import path

from .views import (
    order_list,
    my_orders,
    customer_menu,
    create_online_order,
    add_to_cart,
    cart,
    increase_cart_item,
    decrease_cart_item,
    remove_cart_item,
    clear_cart,
    create_walkin_order,
    order_detail,
    add_order_item,
    place_order,
    cancel_order,
    update_order_status,
    quick_update_order_status,
    order_receipt,
    staff_menu,
)


urlpatterns = [
    path('', order_list, name='order_list'),

    path('my-orders/', my_orders, name='my_orders'),

    path('menu/', customer_menu, name='customer_menu'),
    path('staff-menu/', staff_menu, name='staff_menu'),
    path('online/create/', create_online_order, name='create_online_order'),

    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart, name='cart'),
    path('cart/increase/<int:item_id>/', increase_cart_item, name='increase_cart_item'),
    path('cart/decrease/<int:item_id>/', decrease_cart_item, name='decrease_cart_item'),
    path('cart/remove/<int:item_id>/', remove_cart_item, name='remove_cart_item'),
    path('cart/clear/', clear_cart, name='clear_cart'),

    path('walkin/create/', create_walkin_order, name='create_walkin_order'),

    path('<int:order_id>/receipt/', order_receipt, name='order_receipt'),
    path('<int:order_id>/', order_detail, name='order_detail'),
    path('<int:order_id>/add-item/', add_order_item, name='add_order_item'),
    path('<int:order_id>/place/', place_order, name='place_order'),
    path('<int:order_id>/cancel/', cancel_order, name='cancel_order'),
    path('<int:order_id>/update-status/', update_order_status, name='update_order_status'),
    path('<int:order_id>/quick-status/<str:status>/', quick_update_order_status, name='quick_update_order_status'),
]
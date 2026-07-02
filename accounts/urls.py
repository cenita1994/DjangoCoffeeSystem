from django.urls import path
from .views import (
    customer_register_view,
    login_view,
    logout_view,
    dashboard_redirect,
    customer_dashboard,
    cashier_dashboard,
    manager_dashboard,
    owner_dashboard,
    create_account,
    account_list,
    edit_account,
    deactivate_account,
    reactivate_account,
)

urlpatterns = [
    path('register/', customer_register_view, name='customer_register'),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('dashboard/', dashboard_redirect, name='dashboard'),

    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('cashier/dashboard/', cashier_dashboard, name='cashier_dashboard'),
    path('manager/dashboard/', manager_dashboard, name='manager_dashboard'),
    path('owner/dashboard/', owner_dashboard, name='owner_dashboard'),

    path('accounts/', account_list, name='account_list'),
    path('accounts/create/', create_account, name='create_account'),
    path('accounts/<int:user_id>/edit/', edit_account, name='edit_account'),
    path('accounts/<int:user_id>/deactivate/', deactivate_account, name='deactivate_account'),
    path('accounts/<int:user_id>/reactivate/', reactivate_account, name='reactivate_account'),
]
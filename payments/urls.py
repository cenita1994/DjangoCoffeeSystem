from django.urls import path

from .views import (
    my_wallet,
    wallet_list,
    cash_in,
    wallet_transaction_list,
)


urlpatterns = [
    path('my-wallet/', my_wallet, name='my_wallet'),

    path('wallets/', wallet_list, name='wallet_list'),
    path('cash-in/', cash_in, name='cash_in'),
    path('transactions/', wallet_transaction_list, name='wallet_transaction_list'),
]
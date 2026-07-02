from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CustomerWallet, WalletTransaction


def get_or_create_wallet(customer):
    wallet, created = CustomerWallet.objects.get_or_create(
        customer=customer
    )

    return wallet


def cash_in_wallet(
    customer,
    amount,
    performed_by=None,
    reference='Cash In',
    remarks='',
    payment_method='Cash',
    reference_number=''
):
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError('Cash-in amount must be greater than zero.')

    if payment_method == 'GCash' and not reference_number:
        raise ValidationError('GCash reference number is required.')

    with transaction.atomic():
        wallet, created = CustomerWallet.objects.select_for_update().get_or_create(
            customer=customer
        )

        previous_balance = wallet.balance
        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            customer=customer,
            transaction_type='Cash In',
            payment_method=payment_method,
            reference_number=reference_number,
            amount=amount,
            previous_balance=previous_balance,
            new_balance=wallet.balance,
            reference=reference,
            remarks=remarks,
            performed_by=performed_by
        )

    return wallet


def deduct_wallet(
    customer,
    amount,
    performed_by=None,
    reference='Payment',
    remarks='',
    payment_method='Wallet',
    reference_number=''
):
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError('Payment amount must be greater than zero.')

    with transaction.atomic():
        wallet, created = CustomerWallet.objects.select_for_update().get_or_create(
            customer=customer
        )

        if wallet.balance < amount:
            raise ValidationError('Insufficient wallet balance.')

        previous_balance = wallet.balance
        wallet.balance -= amount
        wallet.save()

        WalletTransaction.objects.create(
            customer=customer,
            transaction_type='Payment',
            payment_method=payment_method,
            reference_number=reference_number,
            amount=amount,
            previous_balance=previous_balance,
            new_balance=wallet.balance,
            reference=reference,
            remarks=remarks,
            performed_by=performed_by
        )

    return wallet


def refund_wallet(
    customer,
    amount,
    performed_by=None,
    reference='Refund',
    remarks='',
    payment_method='Wallet',
    reference_number=''
):
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError('Refund amount must be greater than zero.')

    with transaction.atomic():
        wallet, created = CustomerWallet.objects.select_for_update().get_or_create(
            customer=customer
        )

        previous_balance = wallet.balance
        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            customer=customer,
            transaction_type='Refund',
            payment_method=payment_method,
            reference_number=reference_number,
            amount=amount,
            previous_balance=previous_balance,
            new_balance=wallet.balance,
            reference=reference,
            remarks=remarks,
            performed_by=performed_by
        )

    return wallet
from django.shortcuts import render, redirect
from audittrail.utils import log_audit
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from reports.decorators import open_shift_required

from .forms import CashInForm
from .models import CustomerWallet, WalletTransaction
from .services import cash_in_wallet, get_or_create_wallet
from accounts.decorators import (
    customer_required,
    cashier_manager_or_owner_required,
)


def get_customer_results(search_query):
    if not search_query:
        return []

    customers = User.objects.filter(
        groups__name='Customer'
    ).filter(
        Q(username__icontains=search_query) |
        Q(first_name__icontains=search_query) |
        Q(last_name__icontains=search_query) |
        Q(email__icontains=search_query)
    ).distinct().order_by('username')[:10]

    return list(customers)


@customer_required
def my_wallet(request):
    wallet = get_or_create_wallet(request.user)

    transactions = WalletTransaction.objects.filter(
        customer=request.user
    ).order_by('-transaction_date')[:10]

    return render(request, 'payments/my_wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
    })


@cashier_manager_or_owner_required
def wallet_list(request):
    search_query = request.GET.get('q', '')

    wallets = CustomerWallet.objects.select_related(
        'customer'
    ).all().order_by('customer__username')

    if search_query:
        wallets = wallets.filter(
            Q(customer__username__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query)
        )

    paginator = Paginator(wallets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/wallet_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })


@cashier_manager_or_owner_required
@open_shift_required
def cash_in(request):
    customer_search = request.GET.get('customer_q', '').strip()
    selected_customer_id = ''

    if request.method == 'POST':
        customer_search = request.POST.get('customer_search', '').strip()
        selected_customer_id = request.POST.get('selected_customer_id', '')

        customer_results = get_customer_results(customer_search)

        form = CashInForm(request.POST)

        if form.is_valid():
            customer = form.customer
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            reference_number = form.cleaned_data['reference_number']
            remarks = form.cleaned_data['remarks']

            try:
                wallet = cash_in_wallet(
                    customer=customer,
                    amount=amount,
                    performed_by=request.user,
                    reference='Cash In',
                    remarks=remarks,
                    payment_method=payment_method,
                    reference_number=reference_number
                )

                transaction = WalletTransaction.objects.filter(
                    customer=customer,
                    transaction_type='Cash In',
                    performed_by=request.user
                ).order_by('-transaction_date').first()

                if transaction:
                    log_audit(
                        request=request,
                        action='Payment',
                        module='Payments',
                        description=f'Cash-in wallet for {customer.username}. Amount: {transaction.amount}. Payment method: {payment_method}. Previous balance: {transaction.previous_balance}. New balance: {transaction.new_balance}. Reference No: {reference_number or "N/A"}.',
                        object_type='Wallet Transaction',
                        object_id=transaction.id,
                        object_repr=str(transaction)
                    )

                messages.success(
                    request,
                    f'₱{amount} was successfully added to {customer.username} via {payment_method}.'
                )
                return redirect('wallet_list')

            except ValidationError as error:
                if hasattr(error, 'messages'):
                    messages.error(request, error.messages[0])
                else:
                    messages.error(request, str(error))

    else:
        customer_results = get_customer_results(customer_search)
        form = CashInForm()

    return render(request, 'payments/cash_in_form.html', {
        'form': form,
        'customer_search': customer_search,
        'customer_results': customer_results,
        'selected_customer_id': selected_customer_id,
    })


@cashier_manager_or_owner_required
def wallet_transaction_list(request):
    transaction_types = [
        'Cash In',
        'Payment',
        'Refund',
        'Adjustment',
    ]

    active_type = request.GET.get('type', 'All')
    search_query = request.GET.get('q', '')

    if active_type not in transaction_types and active_type != 'All':
        active_type = 'All'

    transactions = WalletTransaction.objects.select_related(
        'customer',
        'performed_by'
    ).all()

    if active_type != 'All':
        transactions = transactions.filter(transaction_type=active_type)

    if search_query:
        transactions = transactions.filter(
            Q(customer__username__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(reference__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(remarks__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )

    tabs = [
        {
            'name': 'All',
            'count': WalletTransaction.objects.count(),
            'icon': 'bi-list-ul',
        },
        {
            'name': 'Cash In',
            'count': WalletTransaction.objects.filter(transaction_type='Cash In').count(),
            'icon': 'bi-cash-stack',
        },
        {
            'name': 'Payment',
            'count': WalletTransaction.objects.filter(transaction_type='Payment').count(),
            'icon': 'bi-credit-card',
        },
        {
            'name': 'Refund',
            'count': WalletTransaction.objects.filter(transaction_type='Refund').count(),
            'icon': 'bi-arrow-counterclockwise',
        },
        {
            'name': 'Adjustment',
            'count': WalletTransaction.objects.filter(transaction_type='Adjustment').count(),
            'icon': 'bi-sliders',
        },
    ]

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/wallet_transaction_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'active_type': active_type,
        'search_query': search_query,
    })
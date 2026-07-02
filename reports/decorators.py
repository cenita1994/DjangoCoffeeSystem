from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import CashierShift


def user_is_cashier_staff(user):
    return user.groups.filter(
        name__in=['Cashier', 'Manager', 'Owner']
    ).exists()


def get_user_open_shift(user):
    return CashierShift.objects.filter(
        cashier=user,
        status='Open'
    ).first()


def open_shift_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')

        if user_is_cashier_staff(request.user):
            open_shift = get_user_open_shift(request.user)

            if not open_shift:
                messages.warning(
                    request,
                    'Please open your cashier shift first before processing cashier transactions.'
                )
                return redirect('open_cashier_shift')

        return view_func(request, *args, **kwargs)

    return wrapper
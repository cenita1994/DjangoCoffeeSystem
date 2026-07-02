from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def is_customer(user):
    return user.is_authenticated and user.groups.filter(name='Customer').exists()


def is_cashier(user):
    return user.is_authenticated and user.groups.filter(name='Cashier').exists()


def is_manager(user):
    return user.is_authenticated and user.groups.filter(name='Manager').exists()


def is_owner(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Owner').exists()
    )


def is_manager_or_owner(user):
    return user.is_authenticated and (
        user.is_superuser or
        user.groups.filter(name='Manager').exists() or
        user.groups.filter(name='Owner').exists()
    )


def is_cashier_manager_or_owner(user):
    return user.is_authenticated and (
        user.is_superuser or
        user.groups.filter(name='Cashier').exists() or
        user.groups.filter(name='Manager').exists() or
        user.groups.filter(name='Owner').exists()
    )


def is_customer_cashier_manager_or_owner(user):
    return user.is_authenticated and (
        user.is_superuser or
        user.groups.filter(name='Customer').exists() or
        user.groups.filter(name='Cashier').exists() or
        user.groups.filter(name='Manager').exists() or
        user.groups.filter(name='Owner').exists()
    )


def role_required(test_func):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def wrapper(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'Access denied. You are not allowed to open that page.')
            return redirect('dashboard')

        return wrapper

    return decorator


customer_required = role_required(is_customer)
cashier_required = role_required(is_cashier)
manager_required = role_required(is_manager)
owner_required = role_required(is_owner)
manager_or_owner_required = role_required(is_manager_or_owner)
cashier_manager_or_owner_required = role_required(is_cashier_manager_or_owner)
customer_cashier_manager_or_owner_required = role_required(is_customer_cashier_manager_or_owner)
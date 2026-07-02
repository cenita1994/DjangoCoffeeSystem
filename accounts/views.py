from django.shortcuts import render, redirect, get_object_or_404
from audittrail.utils import log_audit
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.urls import reverse

from .forms import CustomerRegistrationForm, EmployeeAccountCreationForm, LoginForm, AccountUpdateForm
from .decorators import (
    customer_required,
    cashier_required,
    manager_or_owner_required,
    owner_required,
)

from orders.models import Order
from inventory.models import Product, Stock
from announcements.models import Announcement, SitePage

def build_public_grouped_menu_products():
    products = Product.objects.select_related(
        'stock',
        'product_category'
    ).all().order_by(
        'product_category__name',
        'name',
        'size'
    )

    size_order = {
        'Regular': 1,
        'Upgrade': 2,
        'Mega': 3,
        'Not Applicable': 4,
    }

    grouped_products = {}
    grouped_lookup = {}

    for product in products:
        category_name = product.display_category()
        product_key = product.name.strip().lower()

        if category_name not in grouped_products:
            grouped_products[category_name] = []
            grouped_lookup[category_name] = {}

        if product_key not in grouped_lookup[category_name]:
            product_group = {
                'name': product.name,
                'category_name': category_name,
                'description': product.description,
                'image': product.image,
                'variants': [],
            }

            grouped_lookup[category_name][product_key] = product_group
            grouped_products[category_name].append(product_group)

        product_group = grouped_lookup[category_name][product_key]

        if product.description and not product_group['description']:
            product_group['description'] = product.description

        if product.image and not product_group['image']:
            product_group['image'] = product.image

        product_group['variants'].append(product)

    for category_name, product_groups in grouped_products.items():
        for product_group in product_groups:
            product_group['variants'].sort(
                key=lambda item: size_order.get(item.size, 99)
            )

    return grouped_products



def get_account_role(user):
    role_order = ['Owner', 'Manager', 'Cashier', 'Customer']

    if user.is_superuser:
        return 'Owner'

    user_groups = set(user.groups.values_list('name', flat=True))

    for role in role_order:
        if role in user_groups:
            return role

    return 'Customer'


def get_account_type_from_role(role):
    if role == 'Customer':
        return 'customers'

    return 'employees'

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    grouped_products = build_public_grouped_menu_products()

    public_announcements = Announcement.objects.filter(
        is_active=True,
        audience='Public'
    ).select_related('created_by')[:3]

    return render(request, 'home.html', {
        'grouped_products': grouped_products,
        'public_announcements': public_announcements,
    })

def about_us_view(request):
    page = SitePage.objects.filter(page_key='about_us', is_active=True).first()

    return render(request, 'about_us.html', {
        'page': page,
    })


def contact_us_view(request):
    page = SitePage.objects.filter(page_key='contact_us', is_active=True).first()

    return render(request, 'contact_us.html', {
        'page': page,
    })

def customer_register_view(request):
    form = CustomerRegistrationForm()

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            customer_group, created = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)

            log_audit(
                request=request,
                user=user,
                action='Create',
                module='User Accounts',
                description=f'Created customer account: {user.username}. Email: {user.email or "N/A"}.',
                object_type='User Account',
                object_id=user.id,
                object_repr=user.username
            )

            login(request, user)
            messages.success(request, 'Customer registration successful. You can now place online orders.')
            return redirect('customer_dashboard')

    return render(request, 'accounts/customer_register.html', {'form': form})


def login_view(request):
    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful.')
            return redirect('dashboard')

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def dashboard_redirect(request):
    user = request.user

    if user.is_superuser or user.groups.filter(name='Owner').exists():
        return redirect('owner_dashboard')

    elif user.groups.filter(name='Manager').exists():
        return redirect('manager_dashboard')

    elif user.groups.filter(name='Cashier').exists():
        return redirect('cashier_dashboard')

    elif user.groups.filter(name='Customer').exists():
        return redirect('customer_dashboard')

    messages.warning(request, 'No role assigned to this account.')
    return redirect('home')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


@customer_required
def customer_dashboard(request):
    customer_announcements = Announcement.objects.filter(
        is_active=True,
        audience__in=['Public', 'Customer']
    ).select_related('created_by')[:5]

    return render(request, 'accounts/customer_dashboard.html', {
        'customer_announcements': customer_announcements,
    })

@cashier_required
def cashier_dashboard(request):
    pending_orders = Order.objects.filter(status='Pending').count()
    preparing_orders = Order.objects.filter(status='Preparing').count()
    ready_orders = Order.objects.filter(status='Ready').count()

    employee_announcements = Announcement.objects.filter(
        is_active=True,
        audience='Employee'
    ).select_related('created_by')[:5]
    
    return render(request, 'accounts/cashier_dashboard.html', {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'employee_announcements': employee_announcements,
    })


@manager_or_owner_required
def manager_dashboard(request):
    pending_orders = Order.objects.filter(status='Pending').count()
    preparing_orders = Order.objects.filter(status='Preparing').count()
    ready_orders = Order.objects.filter(status='Ready').count()

    total_products = Product.objects.count()
    low_stock_products = Stock.objects.filter(
        quantity__lte=F('reorder_level')
    ).count()

    employee_announcements = Announcement.objects.filter(
        is_active=True,
        audience='Employee'
    ).select_related('created_by')[:5]

    return render(request, 'accounts/manager_dashboard.html', {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'employee_announcements': employee_announcements,
    })


@owner_required
def owner_dashboard(request):
    pending_orders = Order.objects.filter(status='Pending').count()
    preparing_orders = Order.objects.filter(status='Preparing').count()
    ready_orders = Order.objects.filter(status='Ready').count()

    total_products = Product.objects.count()
    low_stock_products = Stock.objects.filter(
        quantity__lte=F('reorder_level')
    ).count()

    total_users = User.objects.count()

    employee_announcements = Announcement.objects.filter(
        is_active=True,
        audience='Employee'
    ).select_related('created_by')[:5]

    return render(request, 'accounts/owner_dashboard.html', {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_users': total_users,
        'employee_announcements': employee_announcements,        
    })


@owner_required
def create_account(request):
    form = EmployeeAccountCreationForm()

    if request.method == 'POST':
        form = EmployeeAccountCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            role = form.cleaned_data['role']
            group, created = Group.objects.get_or_create(name=role)
            user.groups.add(group)

            log_audit(
                request=request,
                action='Create',
                module='User Accounts',
                description=f'Created employee account: {user.username}. Role: {role}. Email: {user.email or "N/A"}.',
                object_type='User Account',
                object_id=user.id,
                object_repr=user.username
            )

            messages.success(request, f'{role} account created successfully.')
            return redirect('account_list')

    return render(request, 'accounts/create_account.html', {'form': form})


@owner_required
def account_list(request):
    account_type = request.GET.get('type', 'employees')
    search_query = request.GET.get('q', '')

    if account_type not in ['employees', 'customers']:
        account_type = 'employees'

    employees = User.objects.filter(
        Q(is_superuser=True) |
        Q(groups__name__in=['Cashier', 'Manager', 'Owner'])
    ).distinct()

    customers = User.objects.filter(
        groups__name='Customer'
    ).distinct()

    employee_count = employees.count()
    customer_count = customers.count()

    if account_type == 'customers':
        users = customers
    else:
        users = employees

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    users = users.order_by('username')

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/account_list.html', {
        'page_obj': page_obj,
        'account_type': account_type,
        'search_query': search_query,
        'employee_count': employee_count,
        'customer_count': customer_count,
    })


@owner_required
def edit_account(request, user_id):
    account = get_object_or_404(User, id=user_id)
    current_role = get_account_role(account)

    form = AccountUpdateForm(instance=account, current_role=current_role)

    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=account, current_role=current_role)

        if form.is_valid():
            old_username = account.username
            old_email = account.email or 'N/A'
            old_role = current_role
            old_status = 'Active' if account.is_active else 'Inactive'

            updated_account = form.save(commit=False)
            updated_account.save()

            new_role = form.cleaned_data['role']

            managed_roles = ['Customer', 'Cashier', 'Manager', 'Owner']
            updated_account.groups.remove(*Group.objects.filter(name__in=managed_roles))

            group, created = Group.objects.get_or_create(name=new_role)
            updated_account.groups.add(group)

            new_status = 'Active' if updated_account.is_active else 'Inactive'

            log_audit(
                request=request,
                action='Update',
                module='User Accounts',
                description=(
                    f'Updated account: {old_username} -> {updated_account.username}. '
                    f'Email: {old_email} -> {updated_account.email or "N/A"}. '
                    f'Role: {old_role} -> {new_role}. '
                    f'Status: {old_status} -> {new_status}.'
                ),
                object_type='User Account',
                object_id=updated_account.id,
                object_repr=updated_account.username
            )

            messages.success(request, f'Account {updated_account.username} updated successfully.')
            return redirect(f"{reverse_account_list_url(new_role)}")

    return render(request, 'accounts/edit_account.html', {
        'form': form,
        'account': account,
        'current_role': current_role,
    })


def reverse_account_list_url(role):
    account_type = get_account_type_from_role(role)
    return f'{reverse("account_list")}?type={account_type}'


@owner_required
def deactivate_account(request, user_id):
    account = get_object_or_404(User, id=user_id)

    if request.method != 'POST':
        return redirect('account_list')

    if account == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('account_list')

    if account.is_superuser:
        messages.error(request, 'Superuser accounts cannot be deactivated from this page.')
        return redirect('account_list')

    if not account.is_active:
        messages.info(request, f'Account {account.username} is already inactive.')
        return redirect('account_list')

    role = get_account_role(account)
    account.is_active = False
    account.save(update_fields=['is_active'])

    log_audit(
        request=request,
        action='Archive',
        module='User Accounts',
        description=f'Deactivated/archived account: {account.username}. Role: {role}.',
        object_type='User Account',
        object_id=account.id,
        object_repr=account.username
    )

    messages.success(request, f'Account {account.username} has been deactivated/archived.')
    return redirect(f"{reverse_account_list_url(role)}")


@owner_required
def reactivate_account(request, user_id):
    account = get_object_or_404(User, id=user_id)

    if request.method != 'POST':
        return redirect('account_list')

    if account.is_active:
        messages.info(request, f'Account {account.username} is already active.')
        return redirect('account_list')

    role = get_account_role(account)
    account.is_active = True
    account.save(update_fields=['is_active'])

    log_audit(
        request=request,
        action='Restore',
        module='User Accounts',
        description=f'Reactivated account: {account.username}. Role: {role}.',
        object_type='User Account',
        object_id=account.id,
        object_repr=account.username
    )

    messages.success(request, f'Account {account.username} has been reactivated.')
    return redirect(f"{reverse_account_list_url(role)}")

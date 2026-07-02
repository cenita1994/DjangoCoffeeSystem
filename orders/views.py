from decimal import Decimal
from django.utils import timezone

from django.shortcuts import render, redirect, get_object_or_404
from audittrail.utils import log_audit
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from reports.decorators import open_shift_required

from .models import Order, OrderItem
from .forms import WalkInOrderForm, OrderItemForm, OrderStatusForm, OrderPaymentForm
from .availability import get_product_orderability
from inventory.models import Product, Stock, StockMovement, Ingredient, IngredientMovement
from payments.services import deduct_wallet, refund_wallet
from accounts.decorators import (
    customer_required,
    cashier_manager_or_owner_required,
    customer_cashier_manager_or_owner_required,
)


def user_is_staff_role(user):
    return (
        user.is_superuser or
        user.groups.filter(name='Cashier').exists() or
        user.groups.filter(name='Manager').exists() or
        user.groups.filter(name='Owner').exists()
    )


def user_is_customer(user):
    return user.groups.filter(name='Customer').exists()


def build_grouped_menu_products():
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

        availability = get_product_orderability(product)
        product.is_orderable = availability['is_orderable']
        product.unavailable_reason = availability['reason']
        product.available_servings = availability['available_servings']

        product_group['variants'].append(product)

    for category_name, product_groups in grouped_products.items():
        for product_group in product_groups:
            product_group['variants'] = sorted(
                product_group['variants'],
                key=lambda product: size_order.get(product.size, 99)
            )

    return grouped_products

def get_or_create_customer_draft_order(user):
    draft_order = Order.objects.filter(
        customer=user,
        order_type='Online',
        status='Draft'
    ).first()

    if draft_order:
        return draft_order

    full_name = user.get_full_name()
    customer_name = full_name if full_name else user.username

    return Order.objects.create(
        order_type='Online',
        customer=user,
        customer_name=customer_name,
        status='Draft',
        payment_method='Wallet',
        payment_status='Unpaid'
    )


def add_form_errors_to_messages(request, form):
    for field, errors in form.errors.items():
        if field in form.fields:
            label = form.fields[field].label or field
        else:
            label = 'Error'

        for error in errors:
            messages.error(request, f'{label}: {error}')


def deduct_stock_for_order(order, performed_by=None):
    if order.stock_deducted:
        return

    for item in order.items.select_related('product').all():
        stock = Stock.objects.select_for_update().get(product=item.product)

        previous_quantity = stock.quantity
        stock.quantity -= item.quantity
        stock.save()

        StockMovement.objects.create(
            product=item.product,
            movement_type='Stock Out',
            quantity=item.quantity,
            previous_quantity=previous_quantity,
            new_quantity=stock.quantity,
            reference=f'Order #{order.id}',
            remarks=f'Stock deducted for {order.order_type} order.',
            performed_by=performed_by
        )

    order.stock_deducted = True
    order.save()


def restore_stock_for_order(order, performed_by=None):
    if not order.stock_deducted:
        return

    for item in order.items.select_related('product').all():
        stock, created = Stock.objects.select_for_update().get_or_create(
            product=item.product,
            defaults={
                'quantity': 0,
                'reorder_level': 5,
            }
        )

        previous_quantity = stock.quantity
        stock.quantity += item.quantity
        stock.save()

        StockMovement.objects.create(
            product=item.product,
            movement_type='Return',
            quantity=item.quantity,
            previous_quantity=previous_quantity,
            new_quantity=stock.quantity,
            reference=f'Order #{order.id}',
            remarks=f'Stock returned because {order.order_type} order was cancelled.',
            performed_by=performed_by
        )

    order.stock_deducted = False
    order.save()


def deduct_ingredients_for_order(order, performed_by=None):
    if order.ingredients_deducted:
        return

    movement_count = 0

    for item in order.items.select_related('product').all():
        recipe_items = item.product.recipe_items.select_related('ingredient').filter(
            is_active=True,
            ingredient__is_active=True
        )

        if not recipe_items.exists():
            raise ValidationError(
                f'Recipe is not configured for {item.product}. Please set up the product recipe before placing this order.'
            )

        for recipe_item in recipe_items:
            ingredient = Ingredient.objects.select_for_update().get(id=recipe_item.ingredient_id)
            quantity_needed = recipe_item.quantity_required * item.quantity

            if ingredient.current_quantity < quantity_needed:
                raise ValidationError(
                    f'Not enough {ingredient.name} for {item.product}. '
                    f'Needed: {quantity_needed} {ingredient.unit}. '
                    f'Available: {ingredient.current_quantity} {ingredient.unit}.'
                )

            previous_quantity = ingredient.current_quantity
            ingredient.current_quantity -= quantity_needed
            ingredient.save()

            IngredientMovement.objects.create(
                ingredient=ingredient,
                movement_type='Stock Out',
                quantity=quantity_needed,
                previous_quantity=previous_quantity,
                new_quantity=ingredient.current_quantity,
                reference=f'Order #{order.id}',
                remarks=f'Ingredient deducted for {item.product} x {item.quantity}.',
                performed_by=performed_by
            )

            movement_count += 1

    order.ingredients_deducted = True
    order.save(update_fields=['ingredients_deducted'])

    if movement_count > 0:
        log_audit(
            user=performed_by,
            action='Stock Movement',
            module='Ingredient Management',
            description=f'Deducted ingredients for Order #{order.id} based on product recipes. Ingredient movement records created: {movement_count}.',
            object_type='Order',
            object_id=order.id,
            object_repr=f'Order #{order.id}'
        )


def restore_ingredients_for_order(order, performed_by=None):
    if not order.ingredients_deducted:
        return

    movement_count = 0

    for item in order.items.select_related('product').all():
        recipe_items = item.product.recipe_items.select_related('ingredient').filter(
            is_active=True,
            ingredient__is_active=True
        )

        if not recipe_items.exists():
            raise ValidationError(
                f'Recipe is not configured for {item.product}. Please set up the product recipe before placing this order.'
            )

        for recipe_item in recipe_items:
            ingredient = Ingredient.objects.select_for_update().get(id=recipe_item.ingredient_id)
            quantity_to_restore = recipe_item.quantity_required * item.quantity

            previous_quantity = ingredient.current_quantity
            ingredient.current_quantity += quantity_to_restore
            ingredient.save()

            IngredientMovement.objects.create(
                ingredient=ingredient,
                movement_type='Adjustment',
                quantity=quantity_to_restore,
                previous_quantity=previous_quantity,
                new_quantity=ingredient.current_quantity,
                reference=f'Cancelled Order #{order.id}',
                remarks=f'Ingredient restored because Order #{order.id} was cancelled/refunded.',
                performed_by=performed_by
            )

            movement_count += 1

    order.ingredients_deducted = False
    order.save(update_fields=['ingredients_deducted'])

    if movement_count > 0:
        log_audit(
            user=performed_by,
            action='Stock Movement',
            module='Ingredient Management',
            description=f'Restored ingredients for cancelled Order #{order.id}. Ingredient movement records created: {movement_count}.',
            object_type='Order',
            object_id=order.id,
            object_repr=f'Order #{order.id}'
        )


def process_order_payment(
    order,
    payment_method,
    payment_reference_number='',
    amount_received=0,
    paid_by=None,
    received_by=None
):
    order.update_total()

    total_amount = Decimal(str(order.total_amount or 0))
    amount_received = Decimal(str(amount_received or 0))

    if total_amount <= 0:
        raise ValidationError('Order total amount must be greater than zero.')

    if payment_method == 'Cash':
        if amount_received < total_amount:
            raise ValidationError('Cash received must be equal to or greater than the total amount.')

        change_amount = amount_received - total_amount
        payment_reference_number = ''

    elif payment_method == 'GCash':
        if not payment_reference_number:
            raise ValidationError('GCash reference number is required.')

        amount_received = total_amount
        change_amount = Decimal('0.00')

    elif payment_method == 'Wallet':
        if not order.customer:
            raise ValidationError('Wallet payment requires a customer account.')

        deduct_wallet(
            customer=order.customer,
            amount=total_amount,
            performed_by=received_by,
            reference=f'Order #{order.id}',
            remarks='Wallet payment for order',
            payment_method='Wallet',
            reference_number=''
        )

        amount_received = total_amount
        change_amount = Decimal('0.00')
        payment_reference_number = ''

    else:
        raise ValidationError('Please select a valid payment method.')

    order.payment_method = payment_method
    order.payment_reference_number = payment_reference_number
    order.amount_received = amount_received
    order.change_amount = change_amount
    order.payment_status = 'Paid'
    order.paid_by = paid_by
    order.payment_received_by = received_by
    order.paid_at = timezone.now()

    order.generate_receipt_number()
    order.save()
    
def refund_payment_for_order(order, performed_by=None):
    if order.payment_status != 'Paid':
        return

    if order.payment_method == 'Wallet' and order.customer and order.total_amount > 0:
        refund_wallet(
            customer=order.customer,
            amount=order.total_amount,
            performed_by=performed_by,
            reference=f'Refund Order #{order.id}',
            remarks=f'Refund for cancelled {order.order_type} order.',
            payment_method='Wallet',
            reference_number=''
        )

    order.payment_status = 'Refunded'
    order.save()


@cashier_manager_or_owner_required
def order_list(request):
    status_tabs = [
        'Pending',
        'Preparing',
        'Ready',
        'Completed',
        'Cancelled',
    ]

    active_status = request.GET.get('status', 'Pending')

    if active_status not in status_tabs:
        active_status = 'Pending'

    base_orders = Order.objects.select_related(
        'customer',
        'created_by',
        'paid_by',
        'payment_received_by'
    ).exclude(
        status='Draft'
    )

    status_counts = {}

    for status in status_tabs:
        status_counts[status] = base_orders.filter(status=status).count()

    if active_status in ['Completed', 'Cancelled']:
        orders = base_orders.filter(status=active_status).order_by('-order_date')
    else:
        orders = base_orders.filter(status=active_status).order_by('order_date')

    tabs = [
        {
            'name': 'Pending',
            'count': status_counts['Pending'],
            'icon': 'bi-hourglass-split',
        },
        {
            'name': 'Preparing',
            'count': status_counts['Preparing'],
            'icon': 'bi-cup-hot',
        },
        {
            'name': 'Ready',
            'count': status_counts['Ready'],
            'icon': 'bi-check-circle',
        },
        {
            'name': 'Completed',
            'count': status_counts['Completed'],
            'icon': 'bi-bag-check',
        },
        {
            'name': 'Cancelled',
            'count': status_counts['Cancelled'],
            'icon': 'bi-x-circle',
        },
    ]

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'tabs': tabs,
        'active_status': active_status,
    })


@customer_required
def my_orders(request):
    status_tabs = [
        'Pending',
        'Preparing',
        'Ready',
        'Completed',
        'Cancelled',
    ]

    active_status = request.GET.get('status', 'Pending')

    if active_status not in status_tabs:
        active_status = 'Pending'

    base_orders = Order.objects.filter(
        customer=request.user
    ).exclude(
        status='Draft'
    )

    status_counts = {}

    for status in status_tabs:
        status_counts[status] = base_orders.filter(status=status).count()

    if active_status in ['Completed', 'Cancelled']:
        orders = base_orders.filter(status=active_status).order_by('-order_date')
    else:
        orders = base_orders.filter(status=active_status).order_by('order_date')

    tabs = [
        {
            'name': 'Pending',
            'count': status_counts['Pending'],
            'icon': 'bi-hourglass-split',
        },
        {
            'name': 'Preparing',
            'count': status_counts['Preparing'],
            'icon': 'bi-cup-hot',
        },
        {
            'name': 'Ready',
            'count': status_counts['Ready'],
            'icon': 'bi-check-circle',
        },
        {
            'name': 'Completed',
            'count': status_counts['Completed'],
            'icon': 'bi-bag-check',
        },
        {
            'name': 'Cancelled',
            'count': status_counts['Cancelled'],
            'icon': 'bi-x-circle',
        },
    ]

    return render(request, 'orders/my_orders.html', {
        'orders': orders,
        'tabs': tabs,
        'active_status': active_status,
    })



@customer_required
def customer_menu(request):
    grouped_products = build_grouped_menu_products()

    draft_order = Order.objects.filter(
        customer=request.user,
        order_type='Online',
        status='Draft'
    ).first()

    cart_count = 0

    if draft_order:
        for item in draft_order.items.all():
            cart_count += item.quantity

    return render(request, 'orders/customer_menu.html', {
        'grouped_products': grouped_products,
        'cart_count': cart_count,
    })


@cashier_manager_or_owner_required
def staff_menu(request):
    grouped_products = build_grouped_menu_products()

    return render(request, 'orders/staff_menu.html', {
        'grouped_products': grouped_products,
    })
@customer_required
def create_online_order(request):
    return redirect('customer_menu')


@customer_required
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        stock__quantity__gt=0
    )

    order = get_or_create_customer_draft_order(request.user)

    if request.method == 'POST':
        existing_item = OrderItem.objects.filter(
            order=order,
            product=product
        ).first()

        current_quantity = existing_item.quantity if existing_item else 0
        new_quantity = current_quantity + 1

        availability = get_product_orderability(product, requested_quantity=new_quantity)

        if not availability['is_orderable']:
            messages.error(
                request,
                f'{product} is unavailable. Reason: {availability["reason"]}.'
            )
            return redirect('customer_menu')

        if new_quantity > product.stock.quantity:
            messages.error(
                request,
                f'Cannot add more {product.name}. Available quantity: {product.stock.quantity}.'
            )
            return redirect('customer_menu')


        if existing_item:
            existing_item.quantity = new_quantity

            if not existing_item.cost_price:
                existing_item.cost_price = product.cost_price

            existing_item.save()
        else:
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                price=product.price,
                cost_price=product.cost_price
            )
            

        order.update_total()

        log_audit(
            request=request,
            action='Update' if current_quantity > 0 else 'Create',
            module='Orders',
            description=f'Added product to cart: {product}. Quantity added: 1. Previous cart quantity: {current_quantity}. New cart quantity: {new_quantity}. Order total: {order.total_amount}.',
            object_type='Order Item',
            object_id=existing_item.id if existing_item else None,
            object_repr=str(product)
        )

        messages.success(request, f'{product.name} added to cart.')
        return redirect('customer_menu')

    return redirect('customer_menu')


@customer_required
def cart(request):
    order = Order.objects.filter(
        customer=request.user,
        order_type='Online',
        status='Draft'
    ).first()

    if order:
        order.update_total()

    return render(request, 'orders/cart.html', {'order': order})


@customer_required
def increase_cart_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__customer=request.user,
        order__order_type='Online',
        order__status='Draft'
    )

    if request.method == 'POST':
        try:
            stock = item.product.stock
        except Stock.DoesNotExist:
            messages.error(request, 'This product has no stock record.')
            return redirect('cart')

        if item.quantity + 1 > stock.quantity:
            messages.error(
                request,
                f'Cannot add more {item.product.name}. Available quantity: {stock.quantity}.'
            )
            return redirect('cart')

        old_quantity = item.quantity

        item.quantity += 1
        item.save()
        item.order.update_total()

        log_audit(
            request=request,
            action='Update',
            module='Orders',
            description=f'Increased cart item quantity: {item.product}. Previous quantity: {old_quantity}. New quantity: {item.quantity}. Order total: {item.order.total_amount}.',
            object_type='Order Item',
            object_id=item.id,
            object_repr=str(item.product)
        )

        messages.success(request, f'{item.product.name} quantity updated.')

    return redirect('cart')


@customer_required
def decrease_cart_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__customer=request.user,
        order__order_type='Online',
        order__status='Draft'
    )

    if request.method == 'POST':
        order = item.order

        old_quantity = item.quantity
        product_name = str(item.product)

        if item.quantity > 1:
            item.quantity -= 1
            item.save()

            log_audit(
                request=request,
                action='Update',
                module='Orders',
                description=f'Decreased cart item quantity: {product_name}. Previous quantity: {old_quantity}. New quantity: {item.quantity}.',
                object_type='Order Item',
                object_id=item.id,
                object_repr=product_name
            )

            messages.success(request, f'{item.product.name} quantity updated.')
        else:
            item_id_value = item.id
            item.delete()

            log_audit(
                request=request,
                action='Delete',
                module='Orders',
                description=f'Removed cart item after decreasing quantity: {product_name}. Previous quantity: {old_quantity}.',
                object_type='Order Item',
                object_id=item_id_value,
                object_repr=product_name
            )

            messages.success(request, f'{product_name} removed from cart.')

        order.update_total()

    return redirect('cart')


@customer_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__customer=request.user,
        order__order_type='Online',
        order__status='Draft'
    )

    if request.method == 'POST':
        order = item.order
        product_name = str(item.product)
        removed_quantity = item.quantity
        item_id_value = item.id

        item.delete()
        order.update_total()

        log_audit(
            request=request,
            action='Delete',
            module='Orders',
            description=f'Removed cart item: {product_name}. Removed quantity: {removed_quantity}. Order total after removal: {order.total_amount}.',
            object_type='Order Item',
            object_id=item_id_value,
            object_repr=product_name
        )

        messages.success(request, f'{product_name} removed from cart.')

    return redirect('cart')


@customer_required
def clear_cart(request):
    order = Order.objects.filter(
        customer=request.user,
        order_type='Online',
        status='Draft'
    ).first()

    if request.method == 'POST':
        if order:
            order_id_value = order.id
            item_count = order.items.count()
            total_amount = order.total_amount

            order.items.all().delete()
            order.delete()

            log_audit(
                request=request,
                action='Delete',
                module='Orders',
                description=f'Cleared customer cart. Draft Order #{order_id_value}. Items removed: {item_count}. Previous order total: {total_amount}.',
                object_type='Order',
                object_id=order_id_value,
                object_repr=f'Draft Order #{order_id_value}'
            )

            messages.success(request, 'Cart cleared successfully.')
        else:
            messages.info(request, 'Your cart is already empty.')

    return redirect('cart')



@cashier_manager_or_owner_required
@open_shift_required
def create_walkin_order(request):
    form = WalkInOrderForm()

    if request.method == 'POST':
        form = WalkInOrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            order.order_type = 'Walk-in'
            order.created_by = request.user
            order.status = 'Draft'
            order.payment_status = 'Unpaid'

            if order.customer:
                full_name = order.customer.get_full_name()
                order.customer_name = full_name if full_name else order.customer.username

            order.save()

            log_audit(
                request=request,
                action='Create',
                module='Orders',
                description=f'Created walk-in order #{order.id} for {order.customer_name}. Status: {order.status}. Payment status: {order.payment_status}.',
                object_type='Order',
                object_id=order.id,
                object_repr=f'Order #{order.id}'
            )

            messages.success(request, 'Walk-in order created. Please add products before payment.')
            return redirect('order_detail', order_id=order.id)

    return render(request, 'orders/walkin_order_form.html', {'form': form})


@customer_cashier_manager_or_owner_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            'customer',
            'created_by',
            'paid_by',
            'payment_received_by'
        ),
        id=order_id
    )

    if user_is_customer(request.user) and order.customer != request.user:
        messages.error(request, 'Access denied. You can only view your own orders.')
        return redirect('my_orders')

    order.update_total()

    item_form = OrderItemForm()
    status_form = OrderStatusForm(instance=order)
    payment_form = OrderPaymentForm(instance=order)

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'item_form': item_form,
        'status_form': status_form,
        'payment_form': payment_form,
        'is_staff_role': user_is_staff_role(request.user),
        'is_customer_role': user_is_customer(request.user),
    })


@cashier_manager_or_owner_required
@open_shift_required
def add_order_item(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != 'Draft':
        messages.error(request, 'You can only add products while the order is still in Draft status.')
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        form = OrderItemForm(request.POST)

        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']

            try:
                stock = product.stock
            except Stock.DoesNotExist:
                messages.error(request, 'This product has no stock record.')
                return redirect('order_detail', order_id=order.id)

            existing_item = OrderItem.objects.filter(
                order=order,
                product=product
            ).first()

            current_quantity = existing_item.quantity if existing_item else 0
            new_quantity = current_quantity + quantity

            availability = get_product_orderability(product, requested_quantity=new_quantity)

            if not availability['is_orderable']:
                messages.error(
                    request,
                    f'{product} is unavailable. Reason: {availability["reason"]}.'
                )
                return redirect('order_detail', order_id=order.id)

            if new_quantity > stock.quantity:
                messages.error(
                    request,
                    f'Cannot add {quantity} more {product.name}. Available quantity: {stock.quantity}.'
                )
                return redirect('order_detail', order_id=order.id)


            if existing_item:
                existing_item.quantity = new_quantity

                if not existing_item.cost_price:
                    existing_item.cost_price = product.cost_price

                existing_item.save()
            else:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                    cost_price=product.cost_price
                )


            order.update_total()

            log_audit(
                request=request,
                action='Update',
                module='Orders',
                description=f'Added/updated order item for Order #{order.id}: {product}. Added quantity: {quantity}. Previous quantity: {current_quantity}. New quantity: {new_quantity}. Order total: {order.total_amount}.',
                object_type='Order',
                object_id=order.id,
                object_repr=f'Order #{order.id}'
            )

            messages.success(request, f'{product.name} added to order successfully.')
            return redirect('order_detail', order_id=order.id)

    return redirect('order_detail', order_id=order.id)

@customer_cashier_manager_or_owner_required
@open_shift_required
def place_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != 'Draft':
        messages.error(request, 'Only draft orders can be placed.')
        return redirect('order_detail', order_id=order.id)

    if not order.items.exists():
        messages.error(request, 'Please add at least one product before placing the order.')
        return redirect('order_detail', order_id=order.id)

    order.update_total()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                if order.order_type == 'Online':
                    if request.user != order.customer:
                        messages.error(request, 'You are not allowed to place this online order.')
                        return redirect('order_detail', order_id=order.id)
    
                    process_order_payment(
                        order=order,
                        payment_method='Wallet',
                        payment_reference_number='',
                        amount_received=order.total_amount,
                        paid_by=request.user,
                        received_by=None
                    )
    
                else:
                    payment_form = OrderPaymentForm(request.POST, instance=order)
    
                    if not payment_form.is_valid():
                        add_form_errors_to_messages(request, payment_form)
                        return redirect('order_detail', order_id=order.id)
    
                    process_order_payment(
                        order=order,
                        payment_method=payment_form.cleaned_data['payment_method'],
                        payment_reference_number=payment_form.cleaned_data.get('payment_reference_number') or '',
                        amount_received=payment_form.cleaned_data.get('amount_received') or 0,
                        paid_by=order.customer,
                        received_by=request.user
                    )
    
                deduct_stock_for_order(order, performed_by=request.user)

                deduct_ingredients_for_order(order, performed_by=request.user)
    
                order.status = 'Pending'
                order.save()

            log_audit(
                request=request,
                action='Payment',
                module='Orders',
                description=f'Placed and paid Order #{order.id}. Receipt No: {order.receipt_number}. Total amount: {order.total_amount}. Payment status: {order.payment_status}. Order status changed to Pending.',
                object_type='Order',
                object_id=order.id,
                object_repr=f'Order #{order.id}'
            )

            messages.success(request, f'Order placed successfully. Receipt No: {order.receipt_number}')
            return redirect('order_detail', order_id=order.id)

        except ValidationError as error:
            if hasattr(error, 'messages'):
                messages.error(request, error.messages[0])
            else:
                messages.error(request, str(error))

            return redirect('order_detail', order_id=order.id)

    return redirect('order_detail', order_id=order.id)

@customer_required
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        customer=request.user,
        order_type='Online'
    )

    if order.status != 'Pending':
        messages.error(request, 'You can only cancel orders with Pending status.')
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        old_status = order.status

        with transaction.atomic():
            restore_stock_for_order(order, performed_by=request.user)
            restore_ingredients_for_order(order, performed_by=request.user)
            refund_payment_for_order(order, performed_by=request.user)

            order.status = 'Cancelled'
            order.save()

        log_audit(
            request=request,
            action='Cancel',
            module='Orders',
            description=f'Customer cancelled online Order #{order.id}. Previous status: {old_status}. Payment status: {order.payment_status}. Total amount: {order.total_amount}.',
            object_type='Order',
            object_id=order.id,
            object_repr=f'Order #{order.id}'
        )

        messages.success(request, 'Order cancelled successfully. Payment was refunded if applicable.')
        return redirect('my_orders')

    return redirect('order_detail', order_id=order.id)


@cashier_manager_or_owner_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'Draft':
        messages.error(request, 'Draft orders must be paid and placed first before updating the status.')
        return redirect('order_detail', order_id=order.id)

    if order.status in ['Completed', 'Cancelled']:
        messages.error(request, 'Completed or cancelled orders can no longer be updated.')
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)

        if form.is_valid():
            new_status = form.cleaned_data['status']

            old_status = order.status

            with transaction.atomic():
                if new_status == 'Cancelled':
                    restore_stock_for_order(order, performed_by=request.user)
                    restore_ingredients_for_order(order, performed_by=request.user)
                    refund_payment_for_order(order, performed_by=request.user)

                order.status = new_status
                order.save()

            log_audit(
                request=request,
                action='Cancel' if new_status == 'Cancelled' else 'Status Change',
                module='Orders',
                description=f'Cancelled Order #{order.id} through status update. Previous status: {old_status}. Payment status: {order.payment_status}. Total amount: {order.total_amount}.' if new_status == 'Cancelled' else f'Updated Order #{order.id} status from {old_status} to {new_status}.',
                object_type='Order',
                object_id=order.id,
                object_repr=f'Order #{order.id}'
            )

            messages.success(request, 'Order status updated successfully.')

    return redirect('order_detail', order_id=order.id)


@cashier_manager_or_owner_required
def quick_update_order_status(request, order_id, status):
    order = get_object_or_404(Order, id=order_id)

    allowed_transitions = {
        'Pending': ['Preparing', 'Cancelled'],
        'Preparing': ['Ready', 'Cancelled'],
        'Ready': ['Completed'],
    }

    if request.method == 'POST':
        if order.status in ['Draft', 'Completed', 'Cancelled']:
            messages.error(request, 'This order can no longer be updated.')
            return redirect('order_detail', order_id=order.id)

        if status not in allowed_transitions.get(order.status, []):
            messages.error(request, 'Invalid status update for this order.')
            return redirect('order_detail', order_id=order.id)

        old_status = order.status

        with transaction.atomic():
            if status == 'Cancelled':
                restore_stock_for_order(order, performed_by=request.user)
                restore_ingredients_for_order(order, performed_by=request.user)
                refund_payment_for_order(order, performed_by=request.user)

            order.status = status
            order.save()

        log_audit(
            request=request,
            action='Cancel' if status == 'Cancelled' else 'Status Change',
            module='Orders',
            description=f'Quick cancelled Order #{order.id}. Previous status: {old_status}. Payment status: {order.payment_status}. Total amount: {order.total_amount}.' if status == 'Cancelled' else f'Quick updated Order #{order.id} status from {old_status} to {status}.',
            object_type='Order',
            object_id=order.id,
            object_repr=f'Order #{order.id}'
        )

        messages.success(request, f'Order status updated to {status}.')

    return redirect('order_detail', order_id=order.id)


@customer_cashier_manager_or_owner_required
def order_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not user_is_staff_role(request.user):
        if order.customer != request.user:
            messages.error(request, 'You are not allowed to view this receipt.')
            return redirect('my_orders')

    if order.payment_status != 'Paid':
        messages.error(request, 'Receipt is available only after successful payment.')
        return redirect('order_detail', order_id=order.id)

    order.update_total()

    return render(request, 'orders/order_receipt.html', {
        'order': order,
        'is_staff_role': user_is_staff_role(request.user),
        'is_customer_role': user_is_customer(request.user),
    })
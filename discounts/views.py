from django.shortcuts import render, redirect, get_object_or_404
from audittrail.utils import log_audit
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from orders.models import OrderItem

from .models import DiscountRule, OrderItemDiscount
from .forms import DiscountRuleForm, OrderItemDiscountForm
from .services import apply_order_item_discount, delete_order_item_discount
from accounts.decorators import manager_or_owner_required, cashier_manager_or_owner_required


@manager_or_owner_required
def discount_rule_list(request):
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', 'All')

    categories = [
        'All',
        'Senior',
        'PWD',
        'Promo',
        'Manual',
    ]

    discount_rules = DiscountRule.objects.all().order_by('category', 'name')

    if category_filter != 'All':
        discount_rules = discount_rules.filter(category=category_filter)

    if search_query:
        discount_rules = discount_rules.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    tabs = []

    for category in categories:
        if category == 'All':
            count = DiscountRule.objects.count()
            icon = 'bi-list-ul'
        elif category == 'Senior':
            count = DiscountRule.objects.filter(category='Senior').count()
            icon = 'bi-person-badge'
        elif category == 'PWD':
            count = DiscountRule.objects.filter(category='PWD').count()
            icon = 'bi-person-wheelchair'
        elif category == 'Promo':
            count = DiscountRule.objects.filter(category='Promo').count()
            icon = 'bi-tags'
        else:
            count = DiscountRule.objects.filter(category='Manual').count()
            icon = 'bi-sliders'

        tabs.append({
            'name': category,
            'count': count,
            'icon': icon,
        })

    paginator = Paginator(discount_rules, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'discounts/discount_rule_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'active_category': category_filter,
        'search_query': search_query,
    })


@manager_or_owner_required
def add_discount_rule(request):
    form = DiscountRuleForm()

    if request.method == 'POST':
        form = DiscountRuleForm(request.POST)

        if form.is_valid():
            discount_rule = form.save()

            log_audit(
                request=request,
                action='Create',
                module='Discounts',
                description=f'Created discount rule: {discount_rule.name}. Category: {discount_rule.category}. Type: {discount_rule.discount_type}. Value: {discount_rule.display_value()}.',
                object_type='Discount Rule',
                object_id=discount_rule.id,
                object_repr=discount_rule.name
            )

            messages.success(request, f'{discount_rule.name} added successfully.')
            return redirect('discount_rule_list')

    return render(request, 'discounts/discount_rule_form.html', {
        'form': form,
        'page_title': 'Add Discount Rule',
        'button_text': 'Save Discount Rule',
    })


@manager_or_owner_required
def edit_discount_rule(request, id):
    discount_rule = get_object_or_404(DiscountRule, id=id)
    form = DiscountRuleForm(instance=discount_rule)

    if request.method == 'POST':
        form = DiscountRuleForm(request.POST, instance=discount_rule)

        if form.is_valid():
            old_name = discount_rule.name
            old_value = discount_rule.display_value()

            updated_rule = form.save()

            log_audit(
                request=request,
                action='Update',
                module='Discounts',
                description=f'Updated discount rule: {old_name} to {updated_rule.name}. Previous value: {old_value}. New value: {updated_rule.display_value()}. Category: {updated_rule.category}. Type: {updated_rule.discount_type}.',
                object_type='Discount Rule',
                object_id=updated_rule.id,
                object_repr=updated_rule.name
            )

            messages.success(request, 'Discount rule updated successfully.')
            return redirect('discount_rule_list')

    return render(request, 'discounts/discount_rule_form.html', {
        'form': form,
        'page_title': 'Edit Discount Rule',
        'button_text': 'Update Discount Rule',
    })


@manager_or_owner_required
def delete_discount_rule(request, id):
    discount_rule = get_object_or_404(DiscountRule, id=id)

    if request.method == 'POST':
        rule_name = discount_rule.name
        rule_id = discount_rule.id
        rule_category = discount_rule.category
        rule_type = discount_rule.discount_type
        rule_value = discount_rule.display_value()

        discount_rule.delete()

        log_audit(
            request=request,
            action='Delete',
            module='Discounts',
            description=f'Deleted discount rule: {rule_name}. Category: {rule_category}. Type: {rule_type}. Value: {rule_value}.',
            object_type='Discount Rule',
            object_id=rule_id,
            object_repr=rule_name
        )

        messages.success(request, 'Discount rule deleted successfully.')
        return redirect('discount_rule_list')

    return render(request, 'discounts/discount_rule_delete.html', {
        'discount_rule': discount_rule,
    })


@cashier_manager_or_owner_required
def apply_discount_to_order_item(request, order_item_id):
    order_item = get_object_or_404(
        OrderItem.objects.select_related('order', 'product'),
        id=order_item_id
    )

    if order_item.order.status != 'Draft':
        messages.error(request, 'Discounts can only be applied while the order is still in Draft status.')
        return redirect('order_detail', order_id=order_item.order.id)

    form = OrderItemDiscountForm(order_item=order_item)

    if request.method == 'POST':
        form = OrderItemDiscountForm(request.POST, order_item=order_item)

        if form.is_valid():
            try:
                item_discount = apply_order_item_discount(
                    order_item=order_item,
                    discount_rule=form.cleaned_data['discount_rule'],
                    discounted_quantity=form.cleaned_data['discounted_quantity'],
                    cardholder_name=form.cleaned_data['cardholder_name'],
                    card_number=form.cleaned_data['card_number'],
                    approved_by=request.user,
                    remarks=form.cleaned_data['remarks']
                )

                item_discount.order_item.order.refresh_from_db()

                log_audit(
                    request=request,
                    action='Update',
                    module='Discounts',
                    description=f'Applied discount to Order #{item_discount.order_item.order.id} item {item_discount.order_item.product}. Discount rule: {item_discount.discount_rule.name} ({item_discount.discount_rule.display_value()}). Discounted quantity: {item_discount.discounted_quantity}. Discount amount: {item_discount.discount_amount}. New order total: {item_discount.order_item.order.total_amount}.',
                    object_type='Order Item Discount',
                    object_id=item_discount.id,
                    object_repr=str(item_discount)
                )

                messages.success(request, 'Discount applied successfully.')
                return redirect('order_detail', order_id=order_item.order.id)

            except ValidationError as error:
                if hasattr(error, 'messages'):
                    messages.error(request, error.messages[0])
                else:
                    messages.error(request, str(error))

    return render(request, 'discounts/apply_order_item_discount.html', {
        'form': form,
        'order_item': order_item,
    })


@cashier_manager_or_owner_required
def remove_discount_from_order_item(request, discount_id):
    item_discount = get_object_or_404(
        OrderItemDiscount.objects.select_related(
            'order_item',
            'order_item__order',
            'order_item__product',
            'discount_rule'
        ),
        id=discount_id
    )

    order_id = item_discount.order_item.order.id

    if request.method == 'POST':
        try:
            order = item_discount.order_item.order
            order_id_value = order.id
            product_name = str(item_discount.order_item.product)
            discount_name = item_discount.discount_rule.name
            discount_value = item_discount.discount_rule.display_value()
            discounted_quantity = item_discount.discounted_quantity
            discount_amount = item_discount.discount_amount
            discount_id_value = item_discount.id
            discount_repr = str(item_discount)

            delete_order_item_discount(item_discount)

            order.refresh_from_db()

            log_audit(
                request=request,
                action='Update',
                module='Discounts',
                description=f'Removed discount from Order #{order_id_value} item {product_name}. Discount rule: {discount_name} ({discount_value}). Discounted quantity: {discounted_quantity}. Removed discount amount: {discount_amount}. New order total: {order.total_amount}.',
                object_type='Order Item Discount',
                object_id=discount_id_value,
                object_repr=discount_repr
            )

            messages.success(request, 'Discount removed successfully.')
        except ValidationError as error:
            if hasattr(error, 'messages'):
                messages.error(request, error.messages[0])
            else:
                messages.error(request, str(error))

    return redirect('order_detail', order_id=order_id)
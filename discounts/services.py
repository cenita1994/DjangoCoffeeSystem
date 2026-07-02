from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import OrderItemDiscount


VAT_RATE = Decimal('0.12')


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_total_discounted_quantity(order_item, exclude_discount_id=None):
    discounts = order_item.discounts.all()

    if exclude_discount_id:
        discounts = discounts.exclude(id=exclude_discount_id)

    total = 0

    for discount in discounts:
        total += discount.discounted_quantity

    return total


def get_remaining_discountable_quantity(order_item, exclude_discount_id=None):
    already_discounted = get_total_discounted_quantity(
        order_item,
        exclude_discount_id=exclude_discount_id
    )

    remaining = order_item.quantity - already_discounted

    if remaining < 0:
        return 0

    return remaining


def compute_discount_amount(order_item, discount_rule, discounted_quantity):
    discounted_quantity = int(discounted_quantity)

    item_price = Decimal(str(order_item.price))
    quantity = Decimal(str(discounted_quantity))

    gross_amount = item_price * quantity

    if discount_rule.discount_type == 'Percentage':
        percentage = Decimal(str(discount_rule.percentage))

        if discount_rule.category in ['Senior', 'PWD']:
            vat_exempt_base = gross_amount / (Decimal('1.00') + VAT_RATE)
            discount_amount = vat_exempt_base * (percentage / Decimal('100'))
        else:
            discount_amount = gross_amount * (percentage / Decimal('100'))

    elif discount_rule.discount_type == 'Fixed Amount':
        fixed_amount = Decimal(str(discount_rule.fixed_amount))
        discount_amount = fixed_amount * quantity

        if discount_amount > gross_amount:
            discount_amount = gross_amount

    elif discount_rule.discount_type == 'Buy 1 Take 1':
        free_quantity = discounted_quantity // 2
        discount_amount = item_price * Decimal(str(free_quantity))

    else:
        discount_amount = Decimal('0.00')

    if discount_amount < 0:
        discount_amount = Decimal('0.00')

    if discount_amount > gross_amount:
        discount_amount = gross_amount

    return money(discount_amount)


def apply_order_item_discount(
    order_item,
    discount_rule,
    discounted_quantity,
    cardholder_name='',
    card_number='',
    approved_by=None,
    remarks='',
    existing_discount=None
):
    discounted_quantity = int(discounted_quantity)

    if order_item.order.status != 'Draft':
        raise ValidationError('Discounts can only be applied while the order is still in Draft status.')

    if not discount_rule.is_active:
        raise ValidationError('Selected discount rule is inactive.')

    if discounted_quantity <= 0:
        raise ValidationError('Discounted quantity must be greater than zero.')

    exclude_discount_id = existing_discount.id if existing_discount else None

    remaining_quantity = get_remaining_discountable_quantity(
        order_item,
        exclude_discount_id=exclude_discount_id
    )

    if discounted_quantity > remaining_quantity:
        raise ValidationError(
            f'Discounted quantity cannot exceed remaining discountable quantity. Remaining: {remaining_quantity}.'
        )

    if discount_rule.requires_id_card:
        if not cardholder_name:
            raise ValidationError('Cardholder name is required for this discount.')

        if not card_number:
            raise ValidationError('Card number is required for this discount.')

    discount_amount = compute_discount_amount(
        order_item=order_item,
        discount_rule=discount_rule,
        discounted_quantity=discounted_quantity
    )

    with transaction.atomic():
        if existing_discount:
            item_discount = existing_discount
            item_discount.discount_rule = discount_rule
            item_discount.discounted_quantity = discounted_quantity
            item_discount.cardholder_name = cardholder_name
            item_discount.card_number = card_number
            item_discount.discount_amount = discount_amount
            item_discount.approved_by = approved_by
            item_discount.remarks = remarks
            item_discount.save()
        else:
            item_discount = OrderItemDiscount.objects.create(
                order_item=order_item,
                discount_rule=discount_rule,
                discounted_quantity=discounted_quantity,
                cardholder_name=cardholder_name,
                card_number=card_number,
                discount_amount=discount_amount,
                approved_by=approved_by,
                remarks=remarks
            )

        order_item.order.update_total()

    return item_discount


def delete_order_item_discount(item_discount):
    order = item_discount.order_item.order

    if order.status != 'Draft':
        raise ValidationError('Discounts can only be removed while the order is still in Draft status.')

    with transaction.atomic():
        item_discount.delete()
        order.update_total()
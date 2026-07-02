from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.utils import timezone

from orders.models import OrderItem
from inventory.models import ProductRecipeItem


def decimal_value(value):
    if value is None:
        return Decimal('0.000')

    return Decimal(str(value))


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def quantity(value):
    return Decimal(value).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


def ceil_decimal(value):
    value = Decimal(str(value))

    if value <= 0:
        return Decimal('0')

    rounded_down = value.to_integral_value(rounding='ROUND_FLOOR')

    if value == rounded_down:
        return rounded_down

    return rounded_down + Decimal('1')


def get_default_forecast_dates():
    today = timezone.localdate()
    date_to = today
    date_from = today - timedelta(days=6)

    return date_from, date_to


def get_paid_order_items(date_from, date_to):
    return OrderItem.objects.filter(
        order__payment_status='Paid',
        order__paid_at__isnull=False,
        order__paid_at__date__gte=date_from,
        order__paid_at__date__lte=date_to
    ).exclude(
        order__status='Cancelled'
    ).select_related(
        'order',
        'product',
        'product__product_category'
    )


def build_product_demand_forecast(date_from, date_to, forecast_days=7):
    history_days = (date_to - date_from).days + 1

    if history_days <= 0:
        history_days = 1

    product_map = {}

    for item in get_paid_order_items(date_from, date_to):
        product_id = item.product_id

        if product_id not in product_map:
            product_map[product_id] = {
                'product': item.product,
                'order_count_set': set(),
                'quantity_sold': Decimal('0'),
                'gross_sales': Decimal('0.00'),
                'net_sales': Decimal('0.00'),
                'product_cost': Decimal('0.00'),
                'gross_profit': Decimal('0.00'),
            }

        item_quantity = Decimal(str(item.quantity))
        item_gross = decimal_value(item.subtotal())
        item_discount = decimal_value(item.total_discount())
        item_net = decimal_value(item.net_total())
        item_cost = decimal_value(item.total_cost())
        item_profit = decimal_value(item.estimated_profit())

        product_map[product_id]['order_count_set'].add(item.order_id)
        product_map[product_id]['quantity_sold'] += item_quantity
        product_map[product_id]['gross_sales'] += item_gross
        product_map[product_id]['net_sales'] += item_net
        product_map[product_id]['product_cost'] += item_cost
        product_map[product_id]['gross_profit'] += item_profit

    product_rows = []

    for data in product_map.values():
        product = data['product']
        quantity_sold = data['quantity_sold']

        average_daily_quantity = quantity_sold / Decimal(str(history_days))
        forecast_quantity = ceil_decimal(
            average_daily_quantity * Decimal(str(forecast_days))
        )

        if quantity_sold > 0:
            average_net_price = data['net_sales'] / quantity_sold
            average_cost = data['product_cost'] / quantity_sold
        else:
            average_net_price = Decimal('0.00')
            average_cost = Decimal('0.00')

        projected_sales = average_net_price * forecast_quantity
        projected_cost = average_cost * forecast_quantity
        projected_profit = projected_sales - projected_cost

        product_rows.append({
            'product': product,
            'order_count': len(data['order_count_set']),
            'quantity_sold': quantity_sold,
            'average_daily_quantity': quantity(average_daily_quantity),
            'forecast_quantity': forecast_quantity,
            'gross_sales': money(data['gross_sales']),
            'net_sales': money(data['net_sales']),
            'product_cost': money(data['product_cost']),
            'gross_profit': money(data['gross_profit']),
            'average_net_price': money(average_net_price),
            'average_cost': money(average_cost),
            'projected_sales': money(projected_sales),
            'projected_cost': money(projected_cost),
            'projected_profit': money(projected_profit),
        })

    product_rows = sorted(
        product_rows,
        key=lambda row: row['forecast_quantity'],
        reverse=True
    )

    summary = {
        'history_days': history_days,
        'forecast_days': forecast_days,
        'product_count': len(product_rows),
        'total_quantity_sold': sum(row['quantity_sold'] for row in product_rows),
        'total_forecast_quantity': sum(row['forecast_quantity'] for row in product_rows),
        'total_projected_sales': money(sum(row['projected_sales'] for row in product_rows)),
        'total_projected_cost': money(sum(row['projected_cost'] for row in product_rows)),
        'total_projected_profit': money(sum(row['projected_profit'] for row in product_rows)),
    }

    return product_rows, summary


def build_ingredient_demand_forecast(date_from, date_to, forecast_days=7):
    product_rows, product_summary = build_product_demand_forecast(
        date_from=date_from,
        date_to=date_to,
        forecast_days=forecast_days
    )

    product_forecast_map = {
        row['product'].id: row
        for row in product_rows
    }

    recipe_items = ProductRecipeItem.objects.filter(
        is_active=True,
        product_id__in=product_forecast_map.keys(),
        ingredient__is_active=True
    ).select_related(
        'product',
        'product__product_category',
        'ingredient'
    ).order_by(
        'ingredient__name',
        'product__name',
        'product__size'
    )

    detail_rows = []
    ingredient_summary_map = {}

    for recipe_item in recipe_items:
        product_data = product_forecast_map.get(recipe_item.product_id)

        if not product_data:
            continue

        product = product_data['product']
        ingredient = recipe_item.ingredient

        forecast_quantity = decimal_value(product_data['forecast_quantity'])
        quantity_required = decimal_value(recipe_item.quantity_required)
        safety_buffer_percent = decimal_value(ingredient.safety_buffer_percent)

        projected_used_quantity = forecast_quantity * quantity_required
        buffer_quantity = projected_used_quantity * safety_buffer_percent / Decimal('100')
        recommended_quantity = projected_used_quantity + buffer_quantity

        detail_rows.append({
            'product': product,
            'ingredient': ingredient,
            'forecast_quantity': forecast_quantity,
            'quantity_required': quantity_required,
            'projected_used_quantity': quantity(projected_used_quantity),
            'safety_buffer_percent': safety_buffer_percent,
            'buffer_quantity': quantity(buffer_quantity),
            'recommended_quantity': quantity(recommended_quantity),
        })

        ingredient_id = ingredient.id

        if ingredient_id not in ingredient_summary_map:
            ingredient_summary_map[ingredient_id] = {
                'ingredient': ingredient,
                'projected_used_quantity': Decimal('0.000'),
                'buffer_quantity': Decimal('0.000'),
                'recommended_quantity': Decimal('0.000'),
                'current_quantity': decimal_value(ingredient.current_quantity),
                'reorder_level': decimal_value(ingredient.reorder_level),
                'suggested_purchase_quantity': Decimal('0.000'),
            }

        ingredient_summary_map[ingredient_id]['projected_used_quantity'] += projected_used_quantity
        ingredient_summary_map[ingredient_id]['buffer_quantity'] += buffer_quantity
        ingredient_summary_map[ingredient_id]['recommended_quantity'] += recommended_quantity

    summary_rows = []

    for data in ingredient_summary_map.values():
        suggested_purchase_quantity = data['recommended_quantity'] - data['current_quantity']

        if suggested_purchase_quantity < 0:
            suggested_purchase_quantity = Decimal('0.000')

        data['projected_used_quantity'] = quantity(data['projected_used_quantity'])
        data['buffer_quantity'] = quantity(data['buffer_quantity'])
        data['recommended_quantity'] = quantity(data['recommended_quantity'])
        data['current_quantity'] = quantity(data['current_quantity'])
        data['reorder_level'] = quantity(data['reorder_level'])
        data['suggested_purchase_quantity'] = quantity(suggested_purchase_quantity)

        if data['current_quantity'] <= 0:
            data['status'] = 'Out of Stock'
        elif data['suggested_purchase_quantity'] > 0:
            data['status'] = 'Restock Suggested'
        elif data['current_quantity'] <= data['reorder_level']:
            data['status'] = 'Low Stock'
        else:
            data['status'] = 'Enough Stock'

        summary_rows.append(data)

    summary_rows = sorted(
        summary_rows,
        key=lambda row: row['ingredient'].name
    )

    ingredient_summary = {
        'ingredient_count': len(summary_rows),
        'recipe_item_count': len(detail_rows),
        'total_suggested_purchase_items': sum(
            1 for row in summary_rows if row['suggested_purchase_quantity'] > 0
        ),
    }

    return product_rows, detail_rows, summary_rows, product_summary, ingredient_summary

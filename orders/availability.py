from decimal import Decimal


def get_product_orderability(product, requested_quantity=1):
    try:
        stock = product.stock
    except Exception:
        return {
            'is_orderable': False,
            'reason': 'No availability record',
            'available_servings': 0,
        }

    if stock.quantity <= 0:
        return {
            'is_orderable': False,
            'reason': 'Out of Stock',
            'available_servings': 0,
        }

    if requested_quantity > stock.quantity:
        return {
            'is_orderable': False,
            'reason': f'Only {stock.quantity} available',
            'available_servings': stock.quantity,
        }

    recipe_items = product.recipe_items.select_related('ingredient').filter(
        is_active=True,
        ingredient__is_active=True
    )

    if not recipe_items.exists():
        return {
            'is_orderable': False,
            'reason': 'Recipe not configured',
            'available_servings': 0,
        }

    max_servings_by_ingredients = []

    for recipe_item in recipe_items:
        ingredient = recipe_item.ingredient
        required_per_serving = Decimal(str(recipe_item.quantity_required))

        if required_per_serving <= 0:
            return {
                'is_orderable': False,
                'reason': f'Invalid recipe quantity for {ingredient.name}',
                'available_servings': 0,
            }

        possible_servings = int(ingredient.current_quantity // required_per_serving)

        max_servings_by_ingredients.append(possible_servings)

        quantity_needed = required_per_serving * Decimal(str(requested_quantity))

        if ingredient.current_quantity < quantity_needed:
            return {
                'is_orderable': False,
                'reason': f'Not enough {ingredient.name}',
                'available_servings': min(max_servings_by_ingredients + [stock.quantity]),
            }

    ingredient_servings = min(max_servings_by_ingredients) if max_servings_by_ingredients else 0
    available_servings = min(stock.quantity, ingredient_servings)

    if available_servings <= 0:
        return {
            'is_orderable': False,
            'reason': 'Out of Stock',
            'available_servings': 0,
        }

    return {
        'is_orderable': True,
        'reason': 'Available',
        'available_servings': available_servings,
    }


def get_orderable_product_ids(products):
    orderable_ids = []

    for product in products:
        availability = get_product_orderability(product)

        orderable_ids = []

    for product in products:
        availability = get_product_orderability(product)

        if availability['is_orderable']:
            orderable_ids.append(product.id)

    return orderable_ids

from django.shortcuts import render, redirect, get_object_or_404
from audittrail.utils import log_audit
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q



from .models import Product, ProductCategory, Stock, StockMovement, Ingredient, ProductRecipeItem, IngredientMovement
from .forms import (
    ProductForm,
    ProductCategoryForm,
    StockForm,
    StockInForm,
    IngredientForm,
    ProductRecipeItemForm,
    IngredientStockInForm,
    IngredientAdjustmentForm,
)

from accounts.decorators import manager_or_owner_required


@manager_or_owner_required
def product(request):
    products = Product.objects.select_related('product_category').all().order_by(
        'product_category__name',
        'name'
    )

    return render(request, 'inventory/product_list.html', {
        'products': products
    })


@manager_or_owner_required
def add_product(request):
    form = ProductForm()

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product_item = form.save()

            availability_record, availability_created = Stock.objects.get_or_create(
                product=product_item,
                defaults={
                    'quantity': 0,
                    'reorder_level': 5,
                }
            )

            if availability_created:
                log_audit(
                    request=request,
                    action='Create',
                    module='Product Availability',
                    description=f'Created product availability record for {product_item}. Initial selling limit: 0. Alert level: 5.',
                    object_type='Product Availability',
                    object_id=availability_record.id,
                    object_repr=str(product_item)
                )

            log_audit(
                request=request,
                action='Create',
                module='Product Management',
                description=f'Created product: {product_item}. Product code: {product_item.product_code}. Price: {product_item.price}. Cost: {product_item.cost_price}.',
                object_type='Product',
                object_id=product_item.id,
                object_repr=str(product_item)
            )

            messages.success(request, f'{product_item.name} added successfully.')
            return redirect('product')

    return render(request, 'inventory/product_form.html', {
        'form': form
    })


@manager_or_owner_required
def edit_product(request, id):
    product_item = get_object_or_404(Product, id=id)
    form = ProductForm(instance=product_item)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product_item)

        if form.is_valid():
            old_product_name = str(product_item)
            updated_product = form.save()

            log_audit(
                request=request,
                action='Update',
                module='Product Management',
                description=f'Updated product: {old_product_name} to {updated_product}. Product code: {updated_product.product_code}. Price: {updated_product.price}. Cost: {updated_product.cost_price}.',
                object_type='Product',
                object_id=updated_product.id,
                object_repr=str(updated_product)
            )

            messages.success(request, 'Product updated successfully.')
            return redirect('product')

    return render(request, 'inventory/product_form.html', {
        'form': form
    })


@manager_or_owner_required
def delete_product(request, id):
    product_item = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        product_name = str(product_item)
        product_id = product_item.id
        product_code = product_item.product_code
        price = product_item.price
        cost_price = product_item.cost_price

        product_item.delete()

        log_audit(
            request=request,
            action='Delete',
            module='Product Management',
            description=f'Deleted product: {product_name}. Product code: {product_code}. Price: {price}. Cost: {cost_price}.',
            object_type='Product',
            object_id=product_id,
            object_repr=product_name
        )

        messages.success(request, 'Product deleted successfully.')
        return redirect('product')

    return render(request, 'inventory/delete.html', {
        'product': product_item
    })


@manager_or_owner_required
def category_list(request):
    categories = ProductCategory.objects.prefetch_related('products').all().order_by('name')

    return render(request, 'inventory/category_list.html', {
        'categories': categories
    })


@manager_or_owner_required
def add_category(request):
    form = ProductCategoryForm()

    if request.method == 'POST':
        form = ProductCategoryForm(request.POST)

        if form.is_valid():
            category = form.save()
            messages.success(request, f'{category.name} added successfully.')
            return redirect('category_list')

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'page_title': 'Add Category',
        'button_text': 'Save Category'
    })


@manager_or_owner_required
def edit_category(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    form = ProductCategoryForm(instance=category)

    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, instance=category)

        if form.is_valid():
            category = form.save()

            # Sync edited category name to old Product.category text field.
            category.products.update(category=category.name)

            messages.success(request, 'Category updated successfully.')
            return redirect('category_list')

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'category': category,
        'page_title': 'Edit Category',
        'button_text': 'Update Category'
    })


@manager_or_owner_required
def toggle_category_status(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)

    if request.method == 'POST':
        category.is_active = not category.is_active
        category.save()

        if category.is_active:
            messages.success(request, f'{category.name} has been reactivated.')
        else:
            messages.success(request, f'{category.name} has been deactivated.')

    return redirect('category_list')


@manager_or_owner_required
def delete_category(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)

    if category.products.exists():
        messages.error(
            request,
            'This category cannot be deleted because it still has products. You may deactivate it instead.'
        )
        return redirect('category_list')

    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'{category_name} deleted successfully.')
        return redirect('category_list')

    return render(request, 'inventory/category_confirm_delete.html', {
        'category': category
    })


@manager_or_owner_required
def stock_list(request):
    stocks = Stock.objects.select_related('product').all().order_by('product__name')

    return render(request, 'inventory/stock_list.html', {
        'stocks': stocks
    })


@manager_or_owner_required
def stock_in(request):
    messages.info(
        request,
        'Product Stock In is no longer used. Product deliveries should be recorded under Ingredient Inventory. Product Availability is used only as a customer selling limit.'
    )

    log_audit(
        request=request,
        action='View',
        module='Product Availability',
        description='Accessed old Product Stock In page and was redirected to Product Availability. Product deliveries should be recorded under Ingredient Inventory.',
        object_type='Product Availability',
        object_repr='Legacy Product Stock In Redirect'
    )

    return redirect('stock_list')


@manager_or_owner_required
def stock_movement_list(request):
    movement_types = [
        'Stock In',
        'Stock Out',
        'Adjustment',
        'Return',
    ]

    active_type = request.GET.get('type', 'All')
    search_query = request.GET.get('q', '')

    if active_type not in movement_types and active_type != 'All':
        active_type = 'All'

    movements = StockMovement.objects.select_related(
        'product',
        'performed_by'
    ).all()

    if active_type != 'All':
        movements = movements.filter(movement_type=active_type)

    if search_query:
        movements = movements.filter(
            Q(product__name__icontains=search_query) |
            Q(reference__icontains=search_query) |
            Q(remarks__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )

    tabs = [
        {
            'name': 'All',
            'label': 'All',
            'count': StockMovement.objects.count(),
            'icon': 'bi-list-ul',
        },
        {
            'name': 'Stock In',
            'label': 'Limit Increase',
            'count': StockMovement.objects.filter(movement_type='Stock In').count(),
            'icon': 'bi-plus-circle',
        },
        {
            'name': 'Stock Out',
            'label': 'Limit Deduction',
            'count': StockMovement.objects.filter(movement_type='Stock Out').count(),
            'icon': 'bi-dash-circle',
        },
        {
            'name': 'Adjustment',
            'label': 'Limit Adjustment',
            'count': StockMovement.objects.filter(movement_type='Adjustment').count(),
            'icon': 'bi-sliders',
        },
        {
            'name': 'Return',
            'label': 'Return',
            'count': StockMovement.objects.filter(movement_type='Return').count(),
            'icon': 'bi-arrow-counterclockwise',
        },
    ]

    active_type_label = next(
        (tab['label'] for tab in tabs if tab['name'] == active_type),
        active_type
    )

    paginator = Paginator(movements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/stock_movement_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'active_type': active_type,
        'active_type_label': active_type_label,
        'search_query': search_query,
    })


@manager_or_owner_required
def add_stock(request):
    messages.info(
        request,
        'Add / Update Stock is no longer used. New products automatically receive a Product Availability record. Use Adjust Selling Limit if correction is needed.'
    )

    log_audit(
        request=request,
        action='View',
        module='Product Availability',
        description='Accessed old Add / Update Stock page and was redirected to Product Availability. New products automatically receive availability records.',
        object_type='Product Availability',
        object_repr='Legacy Add / Update Stock Redirect'
    )

    return redirect('stock_list')


@manager_or_owner_required
def edit_stock(request, id):
    stock_item = get_object_or_404(Stock, id=id)
    form = StockForm(instance=stock_item)

    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock_item)

        if form.is_valid():
            with transaction.atomic():
                stock_item = Stock.objects.select_for_update().get(id=id)
                previous_quantity = stock_item.quantity

                updated_stock = form.save()

                if previous_quantity != updated_stock.quantity:
                    difference = abs(updated_stock.quantity - previous_quantity)
                    signed_difference = updated_stock.quantity - previous_quantity

                    StockMovement.objects.create(
                        product=updated_stock.product,
                        movement_type='Adjustment',
                        quantity=difference,
                        previous_quantity=previous_quantity,
                        new_quantity=updated_stock.quantity,
                        reference='Manual Selling Limit Adjustment',
                        remarks='Product selling limit was manually adjusted.',
                        performed_by=request.user
                    )

                    log_audit(
                        request=request,
                        action='Stock Movement',
                        module='Product Availability',
                        description=f'Updated product selling limit for {updated_stock.product}. Previous selling limit: {previous_quantity}. New selling limit: {updated_stock.quantity}. Difference: {signed_difference}.',
                        object_type='Product Availability',
                        object_id=updated_stock.id,
                        object_repr=str(updated_stock.product)
                    )
                else:
                    log_audit(
                        request=request,
                        action='Update',
                        module='Product Availability',
                        description=f'Updated stock record for {updated_stock.product}. Quantity unchanged: {updated_stock.quantity}. Alert level: {updated_stock.reorder_level}.',
                        object_type='Product Availability',
                        object_id=updated_stock.id,
                        object_repr=str(updated_stock.product)
                    )

            messages.success(request, 'Stock record updated successfully.')
            return redirect('stock_list')

    return render(request, 'inventory/stock_form.html', {
        'form': form
    })


@manager_or_owner_required
def delete_stock(request, id):
    messages.warning(
        request,
        'Product Availability records should not be deleted because they control customer ordering. You may set the selling limit to 0 instead.'
    )
    return redirect('stock_list')


@manager_or_owner_required
def ingredient_list(request):
    status_filter = request.GET.get('status', 'All')
    search_query = request.GET.get('q', '')

    ingredients = Ingredient.objects.all().order_by('name')

    if status_filter == 'Active':
        ingredients = ingredients.filter(is_active=True)
    elif status_filter == 'Inactive':
        ingredients = ingredients.filter(is_active=False)
    else:
        status_filter = 'All'

    if search_query:
        ingredients = ingredients.filter(
            Q(name__icontains=search_query)
        )

    tabs = [
        {
            'name': 'All',
            'count': Ingredient.objects.count(),
            'icon': 'bi-list-ul',
        },
        {
            'name': 'Active',
            'count': Ingredient.objects.filter(is_active=True).count(),
            'icon': 'bi-check-circle',
        },
        {
            'name': 'Inactive',
            'count': Ingredient.objects.filter(is_active=False).count(),
            'icon': 'bi-x-circle',
        },
    ]

    paginator = Paginator(ingredients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/ingredient_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'status_filter': status_filter,
        'search_query': search_query,
    })


@manager_or_owner_required
def add_ingredient(request):
    form = IngredientForm()

    if request.method == 'POST':
        form = IngredientForm(request.POST)

        if form.is_valid():
            ingredient = form.save()

            log_audit(
                request=request,
                action='Create',
                module='Ingredient Management',
                description=f'Created ingredient: {ingredient.name}. Initial quantity: {ingredient.current_quantity} {ingredient.unit}. Alert level: {ingredient.reorder_level}.',
                object_type='Ingredient',
                object_id=ingredient.id,
                object_repr=ingredient.name
            )

            messages.success(request, f'{ingredient.name} added successfully.')
            return redirect('ingredient_list')

    return render(request, 'inventory/ingredient_form.html', {
        'form': form,
        'page_title': 'Add Ingredient',
        'button_text': 'Save Ingredient',
    })


@manager_or_owner_required
def edit_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    form = IngredientForm(instance=ingredient)

    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)

        if form.is_valid():
            old_name = ingredient.name
            old_quantity = ingredient.current_quantity
            old_unit = ingredient.unit
            old_reorder_level = ingredient.reorder_level

            updated_ingredient = form.save()

            log_audit(
                request=request,
                action='Update',
                module='Ingredient Management',
                description=f'Updated ingredient: {old_name} to {updated_ingredient.name}. Previous quantity: {old_quantity} {old_unit}. New quantity: {updated_ingredient.current_quantity} {updated_ingredient.unit}. Previous reorder level: {old_reorder_level}. New reorder level: {updated_ingredient.reorder_level}.',
                object_type='Ingredient',
                object_id=updated_ingredient.id,
                object_repr=updated_ingredient.name
            )

            messages.success(request, f'{updated_ingredient.name} updated successfully.')
            return redirect('ingredient_list')

    return render(request, 'inventory/ingredient_form.html', {
        'form': form,
        'ingredient': ingredient,
        'page_title': 'Edit Ingredient',
        'button_text': 'Update Ingredient',
    })


@manager_or_owner_required
def toggle_ingredient_status(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)

    if request.method == 'POST':
        old_status = ingredient.is_active
        ingredient.is_active = not ingredient.is_active
        ingredient.save()

        new_status_text = 'Active' if ingredient.is_active else 'Inactive'
        old_status_text = 'Active' if old_status else 'Inactive'

        log_audit(
            request=request,
            action='Update',
            module='Ingredient Management',
            description=f'Changed ingredient status for {ingredient.name}. Previous status: {old_status_text}. New status: {new_status_text}.',
            object_type='Ingredient',
            object_id=ingredient.id,
            object_repr=ingredient.name
        )

        if ingredient.is_active:
            messages.success(request, f'{ingredient.name} has been reactivated.')
        else:
            messages.success(request, f'{ingredient.name} has been deactivated.')

    return redirect('ingredient_list')


@manager_or_owner_required
def delete_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)

    if ingredient.product_recipes.exists():
        messages.error(
            request,
            'This ingredient cannot be deleted because it is already used in a product recipe. You may deactivate it instead.'
        )
        return redirect('ingredient_list')

    if request.method == 'POST':
        ingredient_name = ingredient.name
        ingredient_id = ingredient.id
        current_quantity = ingredient.current_quantity
        unit = ingredient.unit
        reorder_level = ingredient.reorder_level

        ingredient.delete()

        log_audit(
            request=request,
            action='Delete',
            module='Ingredient Management',
            description=f'Deleted ingredient: {ingredient_name}. Previous quantity: {current_quantity} {unit}. Alert level: {reorder_level}.',
            object_type='Ingredient',
            object_id=ingredient_id,
            object_repr=ingredient_name
        )

        messages.success(request, f'{ingredient_name} deleted successfully.')
        return redirect('ingredient_list')

    return render(request, 'inventory/ingredient_confirm_delete.html', {
        'ingredient': ingredient,
    })



@manager_or_owner_required
def ingredient_stock_in(request):
    form = IngredientStockInForm()

    if request.method == 'POST':
        form = IngredientStockInForm(request.POST)

        if form.is_valid():
            ingredient = form.cleaned_data['ingredient']
            quantity_to_add = form.cleaned_data['quantity']
            reference = form.cleaned_data['reference']
            remarks = form.cleaned_data['remarks']

            with transaction.atomic():
                ingredient = Ingredient.objects.select_for_update().get(
                    id=ingredient.id
                )

                previous_quantity = ingredient.current_quantity
                ingredient.current_quantity += quantity_to_add
                ingredient.save()

                IngredientMovement.objects.create(
                    ingredient=ingredient,
                    movement_type='Stock In',
                    quantity=quantity_to_add,
                    previous_quantity=previous_quantity,
                    new_quantity=ingredient.current_quantity,
                    reference=reference or 'Manual Ingredient Stock In',
                    remarks=remarks,
                    performed_by=request.user
                )

                log_audit(
                    request=request,
                    action='Stock Movement',
                    module='Ingredient Management',
                    description=f'Added {quantity_to_add} {ingredient.unit} to {ingredient.name}. Previous quantity: {previous_quantity}. New quantity: {ingredient.current_quantity}.',
                    object_type='Ingredient Stock',
                    object_id=ingredient.id,
                    object_repr=ingredient.name
                )

            messages.success(
                request,
                f'{quantity_to_add} {ingredient.unit} added to {ingredient.name}.'
            )

            return redirect('ingredient_list')

    return render(request, 'inventory/ingredient_stock_in_form.html', {
        'form': form,
    })



@manager_or_owner_required
def ingredient_adjustment(request):
    form = IngredientAdjustmentForm()

    if request.method == 'POST':
        form = IngredientAdjustmentForm(request.POST)

        if form.is_valid():
            ingredient = form.cleaned_data['ingredient']
            new_quantity = form.cleaned_data['new_quantity']
            reference = form.cleaned_data['reference']
            remarks = form.cleaned_data['remarks']

            with transaction.atomic():
                ingredient = Ingredient.objects.select_for_update().get(
                    id=ingredient.id
                )

                previous_quantity = ingredient.current_quantity
                difference = abs(new_quantity - previous_quantity)

                ingredient.current_quantity = new_quantity
                ingredient.save()

                IngredientMovement.objects.create(
                    ingredient=ingredient,
                    movement_type='Adjustment',
                    quantity=difference,
                    previous_quantity=previous_quantity,
                    new_quantity=ingredient.current_quantity,
                    reference=reference or 'Manual Ingredient Adjustment',
                    remarks=remarks,
                    performed_by=request.user
                )

                signed_difference = ingredient.current_quantity - previous_quantity

                log_audit(
                    request=request,
                    action='Stock Movement',
                    module='Ingredient Management',
                    description=f'Adjusted ingredient stock for {ingredient.name}. Previous quantity: {previous_quantity} {ingredient.unit}. New quantity: {ingredient.current_quantity} {ingredient.unit}. Difference: {signed_difference}.',
                    object_type='Ingredient Stock',
                    object_id=ingredient.id,
                    object_repr=ingredient.name
                )

            messages.success(
                request,
                f'{ingredient.name} quantity adjusted from {previous_quantity} to {new_quantity} {ingredient.unit}.'
            )

            return redirect('ingredient_list')

    return render(request, 'inventory/ingredient_adjustment_form.html', {
        'form': form,
    })

@manager_or_owner_required
def ingredient_movement_list(request):
    movement_types = [
        'Stock In',
        'Stock Out',
        'Adjustment',
    ]

    active_type = request.GET.get('type', 'All')
    search_query = request.GET.get('q', '')

    if active_type not in movement_types and active_type != 'All':
        active_type = 'All'

    movements = IngredientMovement.objects.select_related(
        'ingredient',
        'performed_by'
    ).all()

    if active_type != 'All':
        movements = movements.filter(movement_type=active_type)

    if search_query:
        movements = movements.filter(
            Q(ingredient__name__icontains=search_query) |
            Q(reference__icontains=search_query) |
            Q(remarks__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )

    tabs = [
        {
            'name': 'All',
            'count': IngredientMovement.objects.count(),
            'icon': 'bi-list-ul',
        },
        {
            'name': 'Stock In',
            'count': IngredientMovement.objects.filter(movement_type='Stock In').count(),
            'icon': 'bi-box-arrow-in-down',
        },
        {
            'name': 'Stock Out',
            'count': IngredientMovement.objects.filter(movement_type='Stock Out').count(),
            'icon': 'bi-box-arrow-up',
        },
        {
            'name': 'Adjustment',
            'count': IngredientMovement.objects.filter(movement_type='Adjustment').count(),
            'icon': 'bi-sliders',
        },
    ]

    paginator = Paginator(movements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/ingredient_movement_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'active_type': active_type,
        'active_type_label': active_type_label,
        'search_query': search_query,
    })

@manager_or_owner_required
def recipe_item_list(request):
    status_filter = request.GET.get('status', 'All')
    search_query = request.GET.get('q', '')
    selected_product_id = request.GET.get('product', '')

    recipe_items = ProductRecipeItem.objects.select_related(
        'product',
        'product__product_category',
        'ingredient'
    ).all().order_by(
        'product__product_category__name',
        'product__name',
        'product__size',
        'ingredient__name'
    )

    if status_filter == 'Active':
        recipe_items = recipe_items.filter(is_active=True)
    elif status_filter == 'Inactive':
        recipe_items = recipe_items.filter(is_active=False)
    else:
        status_filter = 'All'

    if selected_product_id:
        recipe_items = recipe_items.filter(product_id=selected_product_id)

    if search_query:
        recipe_items = recipe_items.filter(
            Q(product__name__icontains=search_query) |
            Q(product__product_code__icontains=search_query) |
            Q(product__category__icontains=search_query) |
            Q(product__product_category__name__icontains=search_query) |
            Q(ingredient__name__icontains=search_query)
        )

    products = Product.objects.select_related(
        'product_category'
    ).all().order_by(
        'product_category__name',
        'name',
        'size'
    )

    tabs = [
        {
            'name': 'All',
            'count': ProductRecipeItem.objects.count(),
            'icon': 'bi-list-ul',
        },
        {
            'name': 'Active',
            'count': ProductRecipeItem.objects.filter(is_active=True).count(),
            'icon': 'bi-check-circle',
        },
        {
            'name': 'Inactive',
            'count': ProductRecipeItem.objects.filter(is_active=False).count(),
            'icon': 'bi-x-circle',
        },
    ]

    paginator = Paginator(recipe_items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/recipe_item_list.html', {
        'page_obj': page_obj,
        'tabs': tabs,
        'status_filter': status_filter,
        'search_query': search_query,
        'products': products,
        'selected_product_id': selected_product_id,
    })



@manager_or_owner_required
def add_recipe_item(request):
    selected_product_id = request.GET.get('product', '')

    initial_data = {}

    if selected_product_id:
        initial_data['product'] = selected_product_id

    form = ProductRecipeItemForm(initial=initial_data)

    if request.method == 'POST':
        form = ProductRecipeItemForm(request.POST)

        if form.is_valid():
            recipe_item = form.save()

            log_audit(
                request=request,
                action='Create',
                module='Recipe Management',
                description=f'Added recipe item: {recipe_item.product.display_name()} uses {recipe_item.quantity_required} {recipe_item.ingredient.unit} {recipe_item.ingredient.name}.',
                object_type='Product Recipe Item',
                object_id=recipe_item.id,
                object_repr=str(recipe_item)
            )

            messages.success(
                request,
                f'{recipe_item.ingredient.name} added to {recipe_item.product.display_name()} recipe.'
            )

            if 'save_and_add_another' in request.POST:
                add_url = reverse('add_recipe_item')
                return redirect(f'{add_url}?product={recipe_item.product.id}')

            return redirect('recipe_item_list')

    return render(request, 'inventory/recipe_item_form.html', {
        'form': form,
        'page_title': 'Add Product Recipe Item',
        'button_text': 'Save Recipe Item',
        'is_edit': False,
    })

@manager_or_owner_required
def edit_recipe_item(request, recipe_item_id):
    recipe_item = get_object_or_404(ProductRecipeItem, id=recipe_item_id)
    form = ProductRecipeItemForm(instance=recipe_item)

    if request.method == 'POST':
        form = ProductRecipeItemForm(request.POST, instance=recipe_item)

        if form.is_valid():
            old_product = recipe_item.product.display_name()
            old_ingredient = recipe_item.ingredient.name
            old_quantity = recipe_item.quantity_required
            old_unit = recipe_item.ingredient.unit

            recipe_item = form.save()

            log_audit(
                request=request,
                action='Update',
                module='Recipe Management',
                description=f'Updated recipe item: {old_product} / {old_ingredient}. Previous quantity: {old_quantity} {old_unit}. New recipe: {recipe_item.product.display_name()} / {recipe_item.ingredient.name}, {recipe_item.quantity_required} {recipe_item.ingredient.unit}.',
                object_type='Product Recipe Item',
                object_id=recipe_item.id,
                object_repr=str(recipe_item)
            )

            messages.success(
                request,
                f'{recipe_item.product.display_name()} recipe item updated successfully.'
            )
            return redirect('recipe_item_list')

    return render(request, 'inventory/recipe_item_form.html', {
        'form': form,
        'recipe_item': recipe_item,
        'page_title': 'Edit Product Recipe Item',
        'button_text': 'Update Recipe Item',
        'is_edit': True,
    })


@manager_or_owner_required
def toggle_recipe_item_status(request, recipe_item_id):
    recipe_item = get_object_or_404(ProductRecipeItem, id=recipe_item_id)

    if request.method == 'POST':
        old_status = recipe_item.is_active
        recipe_item.is_active = not recipe_item.is_active
        recipe_item.save()

        old_status_text = 'Active' if old_status else 'Inactive'
        new_status_text = 'Active' if recipe_item.is_active else 'Inactive'

        log_audit(
            request=request,
            action='Update',
            module='Recipe Management',
            description=f'Changed recipe item status for {recipe_item.product.display_name()} / {recipe_item.ingredient.name}. Previous status: {old_status_text}. New status: {new_status_text}.',
            object_type='Product Recipe Item',
            object_id=recipe_item.id,
            object_repr=str(recipe_item)
        )

        if recipe_item.is_active:
            messages.success(request, 'Recipe item has been reactivated.')
        else:
            messages.success(request, 'Recipe item has been deactivated.')

    return redirect('recipe_item_list')


@manager_or_owner_required
def delete_recipe_item(request, recipe_item_id):
    recipe_item = get_object_or_404(ProductRecipeItem, id=recipe_item_id)

    if request.method == 'POST':
        recipe_item_id_value = recipe_item.id
        recipe_item_name = str(recipe_item)
        product_name = recipe_item.product.display_name()
        ingredient_name = recipe_item.ingredient.name
        quantity_required = recipe_item.quantity_required
        unit = recipe_item.ingredient.unit

        recipe_item.delete()

        log_audit(
            request=request,
            action='Delete',
            module='Recipe Management',
            description=f'Deleted recipe item: {product_name} / {ingredient_name}. Quantity required: {quantity_required} {unit}.',
            object_type='Product Recipe Item',
            object_id=recipe_item_id_value,
            object_repr=recipe_item_name
        )

        messages.success(request, 'Recipe item deleted successfully.')
        return redirect('recipe_item_list')

    return render(request, 'inventory/recipe_item_confirm_delete.html', {
        'recipe_item': recipe_item,
    })

def about(request):
    return render(request, 'inventory/about.html')
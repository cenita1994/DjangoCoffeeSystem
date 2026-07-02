from django.urls import path

from .views import (
    product,
    add_product,
    edit_product,
    delete_product,

    category_list,
    add_category,
    edit_category,
    toggle_category_status,
    delete_category,

    stock_list,
    stock_in,
    stock_movement_list,
    add_stock,
    edit_stock,
    delete_stock,

    ingredient_list,
    add_ingredient,
    edit_ingredient,
    toggle_ingredient_status,
    delete_ingredient,
    ingredient_stock_in,
    ingredient_adjustment,
    ingredient_movement_list,

    recipe_item_list,
    add_recipe_item,
    edit_recipe_item,
    toggle_recipe_item_status,
    delete_recipe_item,

    about,
)


urlpatterns = [
    # Product routes
    path('', product, name='product'),
    path('products/', product, name='product'),
    path('products/add/', add_product, name='add_product'),
    path('products/<int:id>/edit/', edit_product, name='edit_product'),
    path('products/<int:id>/delete/', delete_product, name='delete_product'),

    # Product Category routes
    path('categories/', category_list, name='category_list'),
    path('categories/add/', add_category, name='add_category'),
    path('categories/<int:category_id>/edit/', edit_category, name='edit_category'),
    path('categories/<int:category_id>/toggle/', toggle_category_status, name='toggle_category_status'),
    path('categories/<int:category_id>/delete/', delete_category, name='delete_category'),

    # Stock routes
    path('stocks/', stock_list, name='stock_list'),
    path('stocks/add/', add_stock, name='add_stock'),
    path('stocks/<int:id>/edit/', edit_stock, name='edit_stock'),
    path('stocks/<int:id>/delete/', delete_stock, name='delete_stock'),

    # Stock movement routes
    path('stock-in/', stock_in, name='stock_in'),
    path('stock-movements/', stock_movement_list, name='stock_movement_list'),

    # Ingredient routes
    path('ingredients/', ingredient_list, name='ingredient_list'),
    path('ingredients/add/', add_ingredient, name='add_ingredient'),
    path('ingredients/stock-in/', ingredient_stock_in, name='ingredient_stock_in'),
    path('ingredients/adjustment/', ingredient_adjustment, name='ingredient_adjustment'),
    path('ingredients/movements/', ingredient_movement_list, name='ingredient_movement_list'),
    path('ingredients/<int:ingredient_id>/edit/', edit_ingredient, name='edit_ingredient'),
    path('ingredients/<int:ingredient_id>/toggle/', toggle_ingredient_status, name='toggle_ingredient_status'),
    path('ingredients/<int:ingredient_id>/delete/', delete_ingredient, name='delete_ingredient'),

    # Product recipe routes
    path('recipes/', recipe_item_list, name='recipe_item_list'),
    path('recipes/add/', add_recipe_item, name='add_recipe_item'),
    path('recipes/<int:recipe_item_id>/edit/', edit_recipe_item, name='edit_recipe_item'),
    path('recipes/<int:recipe_item_id>/toggle/', toggle_recipe_item_status, name='toggle_recipe_item_status'),
    path('recipes/<int:recipe_item_id>/delete/', delete_recipe_item, name='delete_recipe_item'),

    # About page
    path('about/', about, name='about'),
]
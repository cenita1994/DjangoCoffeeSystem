from django import forms

from .models import (
    Product,
    ProductCategory,
    Stock,
    StockMovement,
    Ingredient,
    ProductRecipeItem,
    IngredientMovement,
)

class ProductForm(forms.ModelForm):
    category_choice = forms.ChoiceField(
        required=False,
        label='Category',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_category_choice'
        })
    )

    new_category = forms.CharField(
        required=False,
        label='New Category',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_new_category',
            'placeholder': 'Enter new category name'
        })
    )

    class Meta:
        model = Product
        fields = [
            'product_code',
            'name',
            'size',
            'price',
            'cost_price',
            'description',
            'image',
        ]

        labels = {
            'product_code': 'Product Code / SKU',
            'name': 'Product Name',
            'size': 'Size',
            'price': 'Selling Price',
            'cost_price': 'Cost Price',
            'description': 'Description',
            'image': 'Image',
        }

        widgets = {
            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated if left blank'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'size': forms.Select(attrs={
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter selling price'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter cost price / puhunan'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter product description'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)

        category_choices = [('', 'Select category')]

        categories = ProductCategory.objects.filter(
            is_active=True
        ).order_by('name')

        for category in categories:
            category_choices.append((str(category.id), category.name))

        category_choices.append(('__other__', 'Others / Add New Category'))

        self.fields['category_choice'].choices = category_choices

        if self.instance and self.instance.pk and self.instance.product_category:
            self.fields['category_choice'].initial = str(self.instance.product_category.id)

    def clean_product_code(self):
        product_code = self.cleaned_data.get('product_code')

        if product_code:
            product_code = product_code.strip().upper()

            existing_product = Product.objects.filter(
                product_code__iexact=product_code
            )

            if self.instance and self.instance.pk:
                existing_product = existing_product.exclude(pk=self.instance.pk)

            if existing_product.exists():
                raise forms.ValidationError('This product code is already used.')

        return product_code

    def clean(self):
        cleaned_data = super().clean()

        selected_category = cleaned_data.get('category_choice')
        new_category = cleaned_data.get('new_category')
        price = cleaned_data.get('price')
        cost_price = cleaned_data.get('cost_price')

        if not selected_category:
            self.add_error('category_choice', 'Please select a category.')

        if selected_category == '__other__':
            if not new_category:
                self.add_error('new_category', 'Please enter the new category name.')
            else:
                cleaned_data['new_category'] = new_category.strip()

        if price is not None and price < 0:
            self.add_error('price', 'Selling price cannot be negative.')

        if cost_price is not None and cost_price < 0:
            self.add_error('cost_price', 'Cost price cannot be negative.')

        if price is not None and cost_price is not None:
            if cost_price > price:
                self.add_error('cost_price', 'Cost price should not be greater than selling price.')

        return cleaned_data

    def save(self, commit=True):
        product = super(ProductForm, self).save(commit=False)

        selected_category = self.cleaned_data.get('category_choice')
        new_category = self.cleaned_data.get('new_category')

        if selected_category == '__other__':
            existing_category = ProductCategory.objects.filter(
                name__iexact=new_category
            ).first()

            if existing_category:
                category = existing_category
            else:
                category = ProductCategory.objects.create(
                    name=new_category,
                    is_active=True
                )

            product.product_category = category
            product.category = category.name

        elif selected_category:
            category = ProductCategory.objects.get(id=selected_category)
            product.product_category = category
            product.category = category.name

        if commit:
            product.save()

        return product

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description', 'is_active']
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'is_active': 'Active',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional category description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if name:
            name = name.strip()

        return name


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'quantity', 'reorder_level']

        labels = {
            'product': 'Product',
            'quantity': 'Selling Limit',
            'reorder_level': 'Alert Level',
        }

        help_texts = {
            'quantity': 'Maximum quantity that customers can still order for this product.',
            'reorder_level': 'Alert level for monitoring low selling limit.',
        }

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Enter selling limit'
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Enter alert level'
            }),
        }


class StockInForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    movement_type = forms.ChoiceField(
        choices=StockMovement.MOVEMENT_TYPE_CHOICES,
        initial='Stock In',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': 'Enter quantity'
        })
    )

    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Example: Delivery Receipt #001'
        })
    )

    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional remarks'
        })
    )
    

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = [
            'name',
            'unit',
            'current_quantity',
            'reorder_level',
            'safety_buffer_percent',
            'is_active',
        ]

        labels = {
            'name': 'Ingredient Name',
            'unit': 'Unit',
            'current_quantity': 'Current Quantity',
            'reorder_level': 'Reorder Level',
            'safety_buffer_percent': 'Safety Buffer Percent',
            'is_active': 'Active',
        }

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Coffee Beans, Milk, Sugar Syrup, Cup'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-control'
            }),
            'current_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': 'Enter current ingredient quantity'
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': 'Enter minimum quantity before restock'
            }),
            'safety_buffer_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Example: 10'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if name:
            name = name.strip()

        return name

    def clean(self):
        cleaned_data = super().clean()

        current_quantity = cleaned_data.get('current_quantity')
        reorder_level = cleaned_data.get('reorder_level')
        safety_buffer_percent = cleaned_data.get('safety_buffer_percent')

        if current_quantity is not None and current_quantity < 0:
            self.add_error('current_quantity', 'Current quantity cannot be negative.')

        if reorder_level is not None and reorder_level < 0:
            self.add_error('reorder_level', 'Reorder level cannot be negative.')

        if safety_buffer_percent is not None and safety_buffer_percent < 0:
            self.add_error('safety_buffer_percent', 'Safety buffer percent cannot be negative.')

        return cleaned_data

class ProductRecipeItemForm(forms.ModelForm):
    class Meta:
        model = ProductRecipeItem
        fields = [
            'product',
            'ingredient',
            'quantity_required',
            'is_active',
        ]

        labels = {
            'product': 'Product / Variant',
            'ingredient': 'Ingredient',
            'quantity_required': 'Quantity Required Per Product',
            'is_active': 'Active',
        }

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ingredient': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity_required': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': 'Example: 18 for grams, 120 for ml, 1 for pc'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ProductRecipeItemForm, self).__init__(*args, **kwargs)

        self.fields['product'].queryset = Product.objects.select_related(
            'product_category'
        ).all().order_by(
            'product_category__name',
            'name',
            'size'
        )

        self.fields['ingredient'].queryset = Ingredient.objects.filter(
            is_active=True
        ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product')
        ingredient = cleaned_data.get('ingredient')
        quantity_required = cleaned_data.get('quantity_required')

        if quantity_required is not None and quantity_required <= 0:
            self.add_error('quantity_required', 'Quantity required must be greater than zero.')

        if product and ingredient:
            existing_recipe_item = ProductRecipeItem.objects.filter(
                product=product,
                ingredient=ingredient
            )

            if self.instance and self.instance.pk:
                existing_recipe_item = existing_recipe_item.exclude(pk=self.instance.pk)

            if existing_recipe_item.exists():
                self.add_error(
                    'ingredient',
                    'This ingredient is already added to the selected product recipe.'
                )

        return cleaned_data

class IngredientStockInForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    quantity = forms.DecimalField(
        min_value=0.001,
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'min': '0.001',
            'placeholder': 'Enter quantity to add'
        })
    )

    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Example: Delivery Receipt #001'
        })
    )

    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional remarks'
        })
    )
    
class IngredientAdjustmentForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    new_quantity = forms.DecimalField(
        min_value=0,
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'min': '0',
            'placeholder': 'Enter new actual quantity'
        })
    )

    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Example: Manual Count, Inventory Audit'
        })
    )

    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional remarks'
        })
    )
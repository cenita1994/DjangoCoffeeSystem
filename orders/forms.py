from decimal import Decimal

from django import forms
from django.contrib.auth.models import User

from .models import Order, OrderItem
from inventory.models import Product
from .availability import get_orderable_product_ids


class WalkInOrderForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(groups__name='Customer').distinct().order_by('username'),
        label='Customer Account',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Order
        fields = ['customer', 'customer_name']

        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter walk-in customer name if no account'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        customer = cleaned_data.get('customer')
        customer_name = cleaned_data.get('customer_name')

        if not customer and not customer_name:
            self.add_error(
                'customer_name',
                'Please select a customer account or enter a walk-in customer name.'
            )

        return cleaned_data


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

        widgets = {
                       
            'product': forms.Select(attrs={
                'class': 'form-control searchable-select',
                'data-placeholder': 'Search product by name, size, price, or stock'
            }),
            
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)

        base_products = Product.objects.filter(
            stock__quantity__gt=0
        ).select_related(
            'stock',
            'product_category'
        ).prefetch_related(
            'recipe_items__ingredient'
        ).order_by(
            'product_category__name',
            'name',
            'size'
        )

        orderable_product_ids = get_orderable_product_ids(base_products)

        self.fields['product'].queryset = Product.objects.filter(
            id__in=orderable_product_ids
        ).select_related(
            'stock',
            'product_category'
        ).order_by(
            'product_category__name',
            'name',
            'size'
        )

        self.fields['product'].label_from_instance = self.product_label

    def product_label(self, product):
        if product.size and product.size != 'Not Applicable':
            product_name = f"{product.name} - {product.size}"
        else:
            product_name = product.name

        try:
            stock_quantity = product.stock.quantity
        except Exception:
            stock_quantity = 0

        return f"{product_name} | ₱{product.price} | Available quantity: {stock_quantity}"

class OrderPaymentForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'payment_method',
            'payment_reference_number',
            'amount_received',
        ]

        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'payment_reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter GCash reference number if applicable'
            }),
            'amount_received': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter cash received'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        payment_method = cleaned_data.get('payment_method')
        payment_reference_number = cleaned_data.get('payment_reference_number')
        amount_received = cleaned_data.get('amount_received') or Decimal('0.00')

        total_amount = Decimal(str(self.instance.total_amount or 0))

        if payment_method == 'None':
            self.add_error(
                'payment_method',
                'Please select a valid payment method.'
            )

        if payment_method == 'Cash':
            if amount_received <= 0:
                self.add_error(
                    'amount_received',
                    'Cash received is required for cash payment.'
                )

            elif amount_received < total_amount:
                self.add_error(
                    'amount_received',
                    'Cash received must be equal to or greater than the total amount.'
                )

            cleaned_data['payment_reference_number'] = ''

        elif payment_method == 'GCash':
            if not payment_reference_number:
                self.add_error(
                    'payment_reference_number',
                    'GCash reference number is required.'
                )

            cleaned_data['amount_received'] = total_amount

        elif payment_method == 'Wallet':
            cleaned_data['payment_reference_number'] = ''
            cleaned_data['amount_received'] = total_amount

        return cleaned_data


class OrderStatusForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[
            ('Pending', 'Pending'),
            ('Preparing', 'Preparing'),
            ('Ready', 'Ready'),
            ('Completed', 'Completed'),
            ('Cancelled', 'Cancelled'),
        ],
        
        widget=forms.Select(attrs={
            'class': 'form-control searchable-select',
            'data-placeholder': 'Search customer account'
         })
    )

    class Meta:
        model = Order
        fields = ['status']


OrderForm = WalkInOrderForm
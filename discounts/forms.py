from django import forms

from .models import DiscountRule, OrderItemDiscount
from .services import get_remaining_discountable_quantity


class DiscountRuleForm(forms.ModelForm):
    class Meta:
        model = DiscountRule
        fields = [
            'name',
            'category',
            'discount_type',
            'percentage',
            'fixed_amount',
            'requires_id_card',
            'is_active',
            'description',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Senior Citizen Discount'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'discount_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Example: 20.00'
            }),
            'fixed_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Example: 50.00'
            }),
            'requires_id_card': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description or rule notes'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        discount_type = cleaned_data.get('discount_type')
        percentage = cleaned_data.get('percentage')
        fixed_amount = cleaned_data.get('fixed_amount')

        if discount_type == 'Percentage':
            if percentage is None or percentage <= 0:
                self.add_error(
                    'percentage',
                    'Percentage must be greater than zero for percentage discount.'
                )

            cleaned_data['fixed_amount'] = 0

        elif discount_type == 'Fixed Amount':
            if fixed_amount is None or fixed_amount <= 0:
                self.add_error(
                    'fixed_amount',
                    'Fixed amount must be greater than zero for fixed amount discount.'
                )

            cleaned_data['percentage'] = 0

        elif discount_type == 'Buy 1 Take 1':
            cleaned_data['percentage'] = 0
            cleaned_data['fixed_amount'] = 0

        return cleaned_data


class OrderItemDiscountForm(forms.ModelForm):
    class Meta:
        model = OrderItemDiscount
        fields = [
            'discount_rule',
            'discounted_quantity',
            'cardholder_name',
            'card_number',
            'remarks',
        ]

        widgets = {
            'discount_rule': forms.Select(attrs={
                'class': 'form-control'
            }),
            'discounted_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'cardholder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter cardholder name'
            }),
            'card_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Senior/PWD ID number'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional remarks'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.order_item = kwargs.pop('order_item', None)
        super(OrderItemDiscountForm, self).__init__(*args, **kwargs)

        self.fields['discount_rule'].queryset = DiscountRule.objects.filter(
            is_active=True
        ).order_by('category', 'name')

    def clean(self):
        cleaned_data = super().clean()

        discount_rule = cleaned_data.get('discount_rule')
        discounted_quantity = cleaned_data.get('discounted_quantity')
        cardholder_name = cleaned_data.get('cardholder_name')
        card_number = cleaned_data.get('card_number')

        if not self.order_item:
            raise forms.ValidationError('Order item is required.')

        if discounted_quantity is None or discounted_quantity <= 0:
            self.add_error(
                'discounted_quantity',
                'Discounted quantity must be greater than zero.'
            )
            return cleaned_data

        remaining_quantity = get_remaining_discountable_quantity(
            self.order_item,
            exclude_discount_id=self.instance.id if self.instance and self.instance.id else None
        )

        if discounted_quantity > remaining_quantity:
            self.add_error(
                'discounted_quantity',
                f'Discounted quantity cannot exceed remaining discountable quantity. Remaining: {remaining_quantity}.'
            )

        if discount_rule and discount_rule.requires_id_card:
            if not cardholder_name:
                self.add_error(
                    'cardholder_name',
                    'Cardholder name is required for this discount.'
                )

            if not card_number:
                self.add_error(
                    'card_number',
                    'Card number is required for this discount.'
                )

        return cleaned_data
from decimal import Decimal

from django import forms
from django.contrib.auth.models import User


class CashInForm(forms.Form):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
    ]

    selected_customer_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput()
    )

    payment_method = forms.ChoiceField(
        label='Payment Method',
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    reference_number = forms.CharField(
        label='GCash Reference Number',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter GCash reference number'
        })
    )

    amount = forms.DecimalField(
        label='Cash-In Amount',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount',
            'step': '0.01'
        })
    )

    remarks = forms.CharField(
        label='Remarks',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional remarks'
        })
    )

    def clean_selected_customer_id(self):
        selected_customer_id = self.cleaned_data.get('selected_customer_id')

        try:
            customer = User.objects.get(
                id=selected_customer_id,
                groups__name='Customer'
            )
        except User.DoesNotExist:
            raise forms.ValidationError('Please select a valid customer account.')

        self.customer = customer
        return selected_customer_id

    def clean(self):
        cleaned_data = super().clean()

        payment_method = cleaned_data.get('payment_method')
        reference_number = cleaned_data.get('reference_number')

        if reference_number:
            reference_number = reference_number.strip()
            cleaned_data['reference_number'] = reference_number

        if payment_method == 'GCash' and not reference_number:
            self.add_error(
                'reference_number',
                'GCash reference number is required.'
            )

        if payment_method == 'Cash':
            cleaned_data['reference_number'] = ''

        return cleaned_data
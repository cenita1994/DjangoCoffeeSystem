from django import forms
from django.contrib.auth.models import User

from .models import CashierShift


def is_manager_or_owner(user):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(
        name__in=['Manager', 'Owner']
    ).exists()


class CashierShiftOpenForm(forms.ModelForm):
    class Meta:
        model = CashierShift
        fields = ['opening_cash']
        labels = {
            'opening_cash': 'Opening Cash / Initial Cash Drawer Amount',
        }
        widgets = {
            'opening_cash': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter opening cash amount'
            }),
        }

    def clean_opening_cash(self):
        opening_cash = self.cleaned_data.get('opening_cash')

        if opening_cash is None:
            opening_cash = 0

        if opening_cash < 0:
            raise forms.ValidationError('Opening cash cannot be negative.')

        return opening_cash


class CashierShiftCloseForm(forms.ModelForm):
    class Meta:
        model = CashierShift
        fields = [
            'actual_cash_counted',
            'cash_payouts',
            'remarks',
        ]
        labels = {
            'actual_cash_counted': 'Actual Cash Counted',
            'cash_payouts': 'Cash Payouts / Expenses / Cash Drops',
            'remarks': 'Remarks',
        }
        widgets = {
            'actual_cash_counted': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter actual cash counted'
            }),
            'cash_payouts': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter cash payouts, expenses, or cash drops'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional remarks about cash drawer, shortage, overage, or shift notes'
            }),
        }

    def clean_actual_cash_counted(self):
        actual_cash_counted = self.cleaned_data.get('actual_cash_counted')

        if actual_cash_counted is None:
            raise forms.ValidationError('Actual cash counted is required.')

        if actual_cash_counted < 0:
            raise forms.ValidationError('Actual cash counted cannot be negative.')

        return actual_cash_counted

    def clean_cash_payouts(self):
        cash_payouts = self.cleaned_data.get('cash_payouts')

        if cash_payouts is None:
            cash_payouts = 0

        if cash_payouts < 0:
            raise forms.ValidationError('Cash payouts cannot be negative.')

        return cash_payouts


class CashierShiftReceiveForm(forms.ModelForm):
    class Meta:
        model = CashierShift
        fields = ['manager_remarks']
        labels = {
            'manager_remarks': 'Manager Remarks',
        }
        widgets = {
            'manager_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional manager remarks after receiving and verifying the cash drawer'
            }),
        }


class CashierShiftFilterForm(forms.Form):
    cashier = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Cashier / Staff',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    status = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('Open', 'Open'),
            ('Closed', 'Closed'),
        ],
        required=False,
        label='Status',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    date_from = forms.DateField(
        required=False,
        label='Date From',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_to = forms.DateField(
        required=False,
        label='Date To',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        if is_manager_or_owner(self.user):
            self.fields['cashier'].queryset = User.objects.filter(
                groups__name__in=['Cashier', 'Manager', 'Owner']
            ).distinct().order_by('username')
        else:
            self.fields.pop('cashier')
from django import forms
from django.utils import timezone
from datetime import timedelta


class ForecastFilterForm(forms.Form):
    FORECAST_DAYS_CHOICES = [
        (7, 'Next 7 Days'),
        (14, 'Next 14 Days'),
        (30, 'Next 30 Days'),
    ]

    date_from = forms.DateField(
        required=True,
        label='Historical Date From',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_to = forms.DateField(
        required=True,
        label='Historical Date To',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    forecast_days = forms.ChoiceField(
        choices=FORECAST_DAYS_CHOICES,
        required=True,
        label='Forecast Horizon',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()
        default_from = today - timedelta(days=6)

        self.fields['date_from'].initial = default_from
        self.fields['date_to'].initial = today
        self.fields['forecast_days'].initial = 7

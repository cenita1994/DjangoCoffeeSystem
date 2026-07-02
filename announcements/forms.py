from django import forms
from .models import Announcement, SitePage


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title',
            'content',
            'image',
            'audience',
            'is_active',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter announcement title',
            }),
            'content': forms.HiddenInput(),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'audience': forms.Select(attrs={
                'class': 'form-control',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')

        if title:
            title = title.strip()

        if not title:
            raise forms.ValidationError('Announcement title is required.')

        return title

    def clean_content(self):
        content = self.cleaned_data.get('content')

        if content:
            content = content.strip()

        if not content:
            raise forms.ValidationError('Announcement content is required.')

        return content

class SitePageForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = [
            'title',
            'subtitle',
            'content',
            'image',
            'location',
            'contact_number',
            'email',
            'store_hours',
            'map_url',
            'is_active',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter page title',
            }),
            'subtitle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short subtitle or intro',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Enter page content',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Brgy. San Jose, Plaridel, Bulacan',
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 0917-245-8821',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: djangocoffee.ph@gmail.com',
            }),
            'store_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Monday to Sunday, 8:00 AM - 9:00 PM',
            }),
            'map_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Google Maps link',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')

        if title:
            title = title.strip()

        if not title:
            raise forms.ValidationError('Page title is required.')

        return title

    def clean_content(self):
        content = self.cleaned_data.get('content')

        if content:
            content = content.strip()

        if not content:
            raise forms.ValidationError('Page content is required.')

        return content


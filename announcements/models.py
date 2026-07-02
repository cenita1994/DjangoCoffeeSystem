from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class Announcement(models.Model):
    AUDIENCE_CHOICES = [
        ('Public', 'Public / Potential Customers'),
        ('Customer', 'Customers'),
        ('Employee', 'Employees'),
    ]

    title = models.CharField(max_length=150)
    content = models.TextField()

    image = models.ImageField(
        upload_to='announcement_images/',
        blank=True,
        null=True
    )

    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='Public'
    )
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_announcements'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'

    def __str__(self):
        return f"{self.title} - {self.audience}"

class SitePage(models.Model):
    PAGE_CHOICES = [
        ('about_us', 'About Us'),
        ('contact_us', 'Contact Us'),
    ]

    page_key = models.CharField(max_length=30, choices=PAGE_CHOICES, unique=True)
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=255, blank=True)
    content = models.TextField()

    image = models.ImageField(
        upload_to='site_page_images/',
        blank=True,
        null=True
    )

    location = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    store_hours = models.CharField(max_length=255, blank=True)
    map_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_site_pages'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page_key']
        verbose_name = 'Site Page'
        verbose_name_plural = 'Site Pages'

    def __str__(self):
        return self.get_page_key_display()


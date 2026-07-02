from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('Login', 'Login'),
        ('Logout', 'Logout'),
        ('Create', 'Create'),
        ('Update', 'Update'),
        ('Delete', 'Delete'),
        ('View', 'View'),
        ('Export', 'Export'),
        ('Payment', 'Payment'),
        ('Cancel', 'Cancel'),
        ('Status Change', 'Status Change'),
        ('Stock Movement', 'Stock Movement'),
        ('System', 'System'),
    ]

    MODULE_CHOICES = [
        ('Authentication', 'Authentication'),
        ('Dashboard', 'Dashboard'),
        ('Orders', 'Orders'),
        ('Payments', 'Payments'),
        ('Discounts', 'Discounts'),
        ('Product Management', 'Product Management'),
        ('Stock Management', 'Stock Management'),
        ('Product Availability', 'Product Availability'),
        ('Ingredient Management', 'Ingredient Management'),
        ('Recipe Management', 'Recipe Management'),
        ('Reports', 'Reports'),
        ('CMS Announcements', 'CMS Announcements'),
        ('User Accounts', 'User Accounts'),
        ('System', 'System'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    username = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    module = models.CharField(max_length=100, choices=MODULE_CHOICES)

    description = models.TextField()

    object_type = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    object_repr = models.CharField(max_length=255, blank=True, null=True)

    url_path = models.CharField(max_length=255, blank=True, null=True)
    http_method = models.CharField(max_length=20, blank=True, null=True)

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user_display = self.username or 'Anonymous'
        return f"{self.created_at} - {user_display} - {self.action} - {self.module}"
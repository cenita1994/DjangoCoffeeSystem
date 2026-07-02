from django.urls import path
from .views import audit_log_list, export_audit_logs

urlpatterns = [
    path('export/', export_audit_logs, name='export_audit_logs'),
    path('', audit_log_list, name='audit_log_list'),
]

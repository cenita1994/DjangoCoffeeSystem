from django.urls import path
from . import views

urlpatterns = [
    path('', views.forecasting_dashboard, name='forecasting_dashboard'),
    path('export/', views.export_forecasting_report, name='export_forecasting_report'),
]

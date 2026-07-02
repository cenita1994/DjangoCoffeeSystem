from django.urls import path
from . import views

urlpatterns = [
    path('', views.menu_assistant, name='menu_assistant'),
    path('history/', views.menu_assistant_history_api, name='menu_assistant_history_api'),
    path('ask/', views.menu_assistant_api, name='menu_assistant_api'),
    path('clear/', views.clear_menu_assistant_api, name='clear_menu_assistant_api'),
]

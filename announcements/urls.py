from django.urls import path
from .views import (
    announcement_list,
    add_announcement,
    edit_announcement,
    toggle_announcement_status,
    delete_announcement,
    site_page_list,
    edit_site_page,
)

urlpatterns = [
    path('', announcement_list, name='announcement_list'),
    path('add/', add_announcement, name='add_announcement'),
    path('<int:announcement_id>/edit/', edit_announcement, name='edit_announcement'),
    path('<int:announcement_id>/toggle/', toggle_announcement_status, name='toggle_announcement_status'),
    path('<int:announcement_id>/delete/', delete_announcement, name='delete_announcement'),

    path('site-pages/', site_page_list, name='site_page_list'),
    path('site-pages/<int:page_id>/edit/', edit_site_page, name='edit_site_page'),
]

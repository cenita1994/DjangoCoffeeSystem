from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from accounts.views import home_view, about_us_view, contact_us_view


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', home_view, name='home'),
    path('about-us/', about_us_view, name='about_us'),
    path('contact-us/', contact_us_view, name='contact_us'),

    # Direct dashboard URL shortcut
    path('dashboard/', lambda request: redirect('dashboard'), name='dashboard_direct'),

    path('accounts/', include('accounts.urls')),
    path('inventory/', include('inventory.urls')),
    path('orders/', include('orders.urls')),
    path('reports/', include('reports.urls')),
    path('forecasting/', include('forecasting.urls')),
    path('menu-assistant/', include('menuassistant.urls')),
    path('payments/', include('payments.urls')),
    path('discounts/', include('discounts.urls')),
    path('announcements/', include('announcements.urls')),
    path('audit-trail/', include('audittrail.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
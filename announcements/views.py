from django.shortcuts import render, redirect, get_object_or_404
from audittrail.utils import log_audit
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from accounts.decorators import manager_or_owner_required
from .models import Announcement, SitePage
from .forms import AnnouncementForm, SitePageForm


@manager_or_owner_required
def announcement_list(request):
    search_query = request.GET.get('q', '').strip()
    audience_filter = request.GET.get('audience', '').strip()
    status_filter = request.GET.get('status', '').strip()

    announcements = Announcement.objects.select_related('created_by').all()

    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )

    if audience_filter:
        announcements = announcements.filter(audience=audience_filter)

    if status_filter == 'active':
        announcements = announcements.filter(is_active=True)
    elif status_filter == 'inactive':
        announcements = announcements.filter(is_active=False)

    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'announcements/announcement_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'audience_filter': audience_filter,
        'status_filter': status_filter,
        'audience_choices': Announcement.AUDIENCE_CHOICES,
    })


@manager_or_owner_required
def add_announcement(request):
    form = AnnouncementForm()

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)

        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()

            log_audit(
                request=request,
                action='Create',
                module='CMS Announcements',
                description=f'Created announcement: {announcement.title}. Audience: {announcement.audience}. Active: {announcement.is_active}.',
                object_type='Announcement',
                object_id=announcement.id,
                object_repr=announcement.title
            )

            messages.success(request, 'Announcement created successfully.')
            return redirect('announcement_list')

    return render(request, 'announcements/announcement_form.html', {
        'form': form,
        'title': 'Add Announcement',
        'button_label': 'Save Announcement',
    })


@manager_or_owner_required
def edit_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    form = AnnouncementForm(instance=announcement)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)

        if form.is_valid():
            old_title = announcement.title
            old_audience = announcement.audience
            old_status = announcement.is_active

            updated_announcement = form.save()

            log_audit(
                request=request,
                action='Update',
                module='CMS Announcements',
                description=f'Updated announcement: {old_title} to {updated_announcement.title}. Previous audience: {old_audience}. New audience: {updated_announcement.audience}. Previous active: {old_status}. New active: {updated_announcement.is_active}.',
                object_type='Announcement',
                object_id=updated_announcement.id,
                object_repr=updated_announcement.title
            )

            messages.success(request, 'Announcement updated successfully.')
            return redirect('announcement_list')

    return render(request, 'announcements/announcement_form.html', {
        'form': form,
        'title': 'Edit Announcement',
        'button_label': 'Update Announcement',
    })


@manager_or_owner_required
def toggle_announcement_status(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    old_status = announcement.is_active
    announcement.is_active = not announcement.is_active
    announcement.save()

    old_status_text = 'Active' if old_status else 'Inactive'
    new_status_text = 'Active' if announcement.is_active else 'Inactive'

    log_audit(
        request=request,
        action='Update',
        module='CMS Announcements',
        description=f'Changed announcement status for {announcement.title}. Previous status: {old_status_text}. New status: {new_status_text}. Audience: {announcement.audience}.',
        object_type='Announcement',
        object_id=announcement.id,
        object_repr=announcement.title
    )

    if announcement.is_active:
        messages.success(request, 'Announcement activated successfully.')
    else:
        messages.warning(request, 'Announcement deactivated successfully.')

    return redirect('announcement_list')


@manager_or_owner_required
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.method == 'POST':
        announcement_title = announcement.title
        announcement_id_value = announcement.id
        audience = announcement.audience
        is_active = announcement.is_active

        announcement.delete()

        log_audit(
            request=request,
            action='Delete',
            module='CMS Announcements',
            description=f'Deleted announcement: {announcement_title}. Audience: {audience}. Active before deletion: {is_active}.',
            object_type='Announcement',
            object_id=announcement_id_value,
            object_repr=announcement_title
        )

        messages.success(request, 'Announcement deleted successfully.')
        return redirect('announcement_list')

    return render(request, 'announcements/announcement_confirm_delete.html', {
        'announcement': announcement,
    })


def ensure_default_site_pages():
    defaults = {
        'about_us': {
            'title': 'Serving coffee, comfort, and convenience.',
            'subtitle': 'About Our Coffee Shop',
            'content': (
                'Django Coffee System is a sample coffee shop ordering and inventory platform designed to support '
                'smoother customer ordering, cashier-assisted transactions, product monitoring, and business reporting.'
            ),
        },
        'contact_us': {
            'title': 'Visit us or get in touch.',
            'subtitle': 'For product inquiries, online ordering concerns, and coffee shop updates, you may contact us through the details below.',
            'content': 'We are ready to assist you with product inquiries, online ordering concerns, and coffee shop updates.',
            'location': 'Brgy. San Jose, Plaridel, Bulacan',
            'contact_number': '0917-245-8821',
            'email': 'djangocoffee.ph@gmail.com',
            'store_hours': 'Monday to Sunday, 8:00 AM - 9:00 PM',
            'map_url': 'https://www.google.com/maps/search/?api=1&query=Brgy.%20San%20Jose%2C%20Plaridel%2C%20Bulacan',
        },
    }

    for page_key, page_defaults in defaults.items():
        SitePage.objects.get_or_create(
            page_key=page_key,
            defaults=page_defaults
        )


@manager_or_owner_required
def site_page_list(request):
    ensure_default_site_pages()

    pages = SitePage.objects.select_related('updated_by').all()

    return render(request, 'announcements/site_page_list.html', {
        'pages': pages,
    })


@manager_or_owner_required
def edit_site_page(request, page_id):
    ensure_default_site_pages()

    page = get_object_or_404(SitePage, id=page_id)
    form = SitePageForm(instance=page)

    if request.method == 'POST':
        form = SitePageForm(request.POST, request.FILES, instance=page)

        if form.is_valid():
            old_title = page.title
            old_status = page.is_active

            site_page = form.save(commit=False)
            site_page.updated_by = request.user
            site_page.save()

            log_audit(
                request=request,
                action='Update',
                module='CMS Site Pages',
                description=(
                    f'Updated site page: {site_page.get_page_key_display()}. '
                    f'Title: {old_title} -> {site_page.title}. '
                    f'Active: {old_status} -> {site_page.is_active}.'
                ),
                object_type='Site Page',
                object_id=site_page.id,
                object_repr=site_page.get_page_key_display()
            )

            messages.success(request, f'{site_page.get_page_key_display()} page updated successfully.')
            return redirect('site_page_list')

    return render(request, 'announcements/site_page_form.html', {
        'form': form,
        'page': page,
        'title': f'Edit {page.get_page_key_display()} Page',
        'button_label': 'Update Page',
    })


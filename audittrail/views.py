import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.http import HttpResponse

from .models import AuditLog
from .utils import log_audit


def owner_only(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        is_owner = request.user.groups.filter(name='Owner').exists()

        if request.user.is_superuser or is_owner:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You are not allowed to access the audit trail.')
        return redirect('dashboard')

    return wrapper


@owner_only
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user').all()

    search_query = request.GET.get('q', '').strip()
    user_filter = request.GET.get('user', '').strip()
    role_filter = request.GET.get('role', '').strip()
    account_type = request.GET.get('account_type', '').strip()
    action_filter = request.GET.get('action', '').strip()
    module_filter = request.GET.get('module', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search_query:
        logs = logs.filter(
            Q(username__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(module__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )

    if account_type == 'employees':
        logs = logs.exclude(role='Customer').exclude(role='Anonymous')
    elif account_type == 'customers':
        logs = logs.filter(role='Customer')

    if user_filter:
        logs = logs.filter(username=user_filter)

    if role_filter:
        logs = logs.filter(role=role_filter)

    if action_filter:
        logs = logs.filter(action=action_filter)

    if module_filter:
        logs = logs.filter(module=module_filter)

    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    usernames = AuditLog.objects.exclude(username__isnull=True).exclude(username='').exclude(role='Customer').values_list('username', flat=True).distinct().order_by('username')

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop('page', None)
    query_string = params.urlencode()
    page_url_prefix = f'?{query_string}&' if query_string else '?'
    export_query_string = query_string

    return render(request, 'audittrail/audit_log_list.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'page_url_prefix': page_url_prefix,
        'export_query_string': export_query_string,
        'total_logs': logs.count(),
        'search_query': search_query,
        'user_filter': user_filter,
        'role_filter': role_filter,
        'account_type': account_type,
        'action_filter': action_filter,
        'module_filter': module_filter,
        'date_from': date_from,
        'date_to': date_to,
        'usernames': usernames,
        'roles': AuditLog.objects.exclude(role__isnull=True).exclude(role='').values_list('role', flat=True).distinct().order_by('role'),
        'action_choices': AuditLog.ACTION_CHOICES,
        'module_choices': AuditLog.MODULE_CHOICES,
    })


@owner_only
def export_audit_logs(request):
    logs = AuditLog.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    account_type = request.GET.get('account_type', '').strip()
    user = request.GET.get('user', '').strip()
    role = request.GET.get('role', '').strip()
    action = request.GET.get('action', '').strip()
    module = request.GET.get('module', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        logs = logs.filter(
            Q(username__icontains=q) |
            Q(role__icontains=q) |
            Q(action__icontains=q) |
            Q(module__icontains=q) |
            Q(description__icontains=q) |
            Q(ip_address__icontains=q)
        )

    if account_type == 'employees':
        logs = logs.exclude(role='Customer').exclude(role='Anonymous')
    elif account_type == 'customers':
        logs = logs.filter(role='Customer')

    if user:
        logs = logs.filter(username=user)

    if role:
        logs = logs.filter(role=role)

    if action:
        logs = logs.filter(action=action)

    if module:
        logs = logs.filter(module=module)

    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    log_audit(
        request=request,
        action='Export',
        module='System',
        description=f'Exported audit trail CSV. Records exported: {logs.count()}.',
        object_type='Audit Log',
        object_repr='Audit Trail CSV'
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_trail.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date/Time', 'User', 'Role', 'Action', 'Module', 'Description', 'IP Address', 'Device/Browser'])

    for log in logs:
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.username or 'Anonymous',
            log.role or 'N/A',
            log.action,
            log.module,
            log.description,
            log.ip_address or 'N/A',
            log.user_agent or 'N/A',
        ])

    return response

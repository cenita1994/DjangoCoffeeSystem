from datetime import timedelta
from django.utils import timezone

from .models import AuditLog


def get_client_ip(request):
    if not request:
        return None

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if forwarded_for:
        ip_address = forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    return ip_address


def get_user_role(user):
    if not user or not user.is_authenticated:
        return 'Anonymous'

    group = user.groups.first()

    if group:
        return group.name

    if user.is_superuser:
        return 'Superuser'

    return 'User'


def log_audit(
    request=None,
    action='System',
    module='System',
    description='',
    user=None,
    object_type=None,
    object_id=None,
    object_repr=None
):
    try:
        if user is None and request is not None:
            user = request.user if request.user.is_authenticated else None

        username = None
        role = None

        if user and user.is_authenticated:
            username = user.username
            role = get_user_role(user)
        else:
            role = 'Anonymous'

        duplicate_exists = AuditLog.objects.filter(
            user=user if user and user.is_authenticated else None,
            action=action,
            module=module,
            description=description,
            url_path=request.path if request else None,
            created_at__gte=timezone.now() - timedelta(seconds=3)
        ).exists()

        if duplicate_exists:
            return

        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            username=username,
            role=role,
            action=action,
            module=module,
            description=description,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else None,
            object_repr=str(object_repr) if object_repr is not None else None,
            url_path=request.path if request else None,
            http_method=request.method if request else None,
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None,
        )

        if request is not None:
            request._manual_audit_logged = True

    except Exception:
        # Audit logging should never break the main system process.
        pass

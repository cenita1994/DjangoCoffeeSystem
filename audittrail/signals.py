from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .utils import log_audit


@receiver(user_logged_in)
def audit_user_logged_in(sender, request, user, **kwargs):
    log_audit(
        request=request,
        user=user,
        action='Login',
        module='Authentication',
        description=f'{user.username} logged in successfully.'
    )


@receiver(user_logged_out)
def audit_user_logged_out(sender, request, user, **kwargs):
    log_audit(
        request=request,
        user=user,
        action='Logout',
        module='Authentication',
        description=f'{user.username if user else "Unknown user"} logged out.'
    )


@receiver(user_login_failed)
def audit_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'Unknown')

    log_audit(
        request=request,
        action='System',
        module='Authentication',
        description=f'Failed login attempt for username: {username}.'
    )

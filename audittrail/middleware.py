from .utils import log_audit


class AuditTrailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_module(self, path):
        if path.startswith('/dashboard'):
            return 'Dashboard'
        if path.startswith('/inventory/stocks') or path.startswith('/inventory/stock-in') or path.startswith('/stocks'):
            return 'Product Availability'
        if path.startswith('/inventory/ingredients'):
            return 'Ingredient Management'
        if path.startswith('/inventory/recipes') or path.startswith('/inventory/recipe'):
            return 'Recipe Management'
        if path.startswith('/inventory/products') or path.startswith('/products'):
            return 'Product Management'
        if path.startswith('/orders'):
            return 'Orders'
        if path.startswith('/payments'):
            return 'Payments'
        if path.startswith('/discounts'):
            return 'Discounts'
        if path.startswith('/reports'):
            return 'Reports'
        if path.startswith('/announcements'):
            return 'CMS Announcements'
        if path.startswith('/audit-trail'):
            return 'System'
        if path.startswith('/accounts'):
            return 'User Accounts'
        if path.startswith('/inventory'):
            return 'Product Management'
        return None

    def get_action(self, path, method):
        lower_path = path.lower()

        if method == 'GET':
            return 'View'
        if 'delete' in lower_path:
            return 'Delete'
        if 'cancel' in lower_path:
            return 'Cancel'
        if 'quick-status' in lower_path or 'status' in lower_path:
            return 'Status Change'
        if 'place' in lower_path or 'payment' in lower_path or 'pay' in lower_path:
            return 'Payment'
        if 'stock' in lower_path:
            return 'Stock Movement'
        if 'discount' in lower_path or 'apply' in lower_path or 'remove' in lower_path:
            return 'Update'
        if 'edit' in lower_path or 'update' in lower_path:
            return 'Update'
        if 'add' in lower_path or 'create' in lower_path:
            return 'Create'

        return 'System'

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            path = request.path
            module = self.get_module(path)

            if path in ['/accounts/login/', '/accounts/logout/']:
                return response

            if module:
                action = self.get_action(path, request.method)

                if request.method == 'GET' and not getattr(request, '_manual_audit_logged', False):
                    session_key = f'audit_viewed_{path}'

                    if not request.session.get(session_key):
                        log_audit(
                            request=request,
                            action=action,
                            module=module,
                            description=f'Opened page: {path}'
                        )
                        request.session[session_key] = True

                elif request.method == 'POST' and response.status_code < 400 and not getattr(request, '_manual_audit_logged', False):
                    log_audit(
                        request=request,
                        action=action,
                        module=module,
                        description=f'Performed {action} action at: {path}'
                    )

        return response

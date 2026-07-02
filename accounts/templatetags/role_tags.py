from django import template

register = template.Library()


@register.filter
def has_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


@register.filter
def is_customer_role(user):
    return user.is_authenticated and user.groups.filter(name='Customer').exists()


@register.filter
def is_cashier_role(user):
    return user.is_authenticated and user.groups.filter(name='Cashier').exists()


@register.filter
def is_manager_role(user):
    return user.is_authenticated and user.groups.filter(name='Manager').exists()


@register.filter
def is_owner_role(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Owner').exists()
    )
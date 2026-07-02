def user_role_flags(request):
    is_owner_user = False

    if request.user.is_authenticated:
        is_owner_user = (
            request.user.is_superuser or
            request.user.groups.filter(name='Owner').exists()
        )

    return {
        'is_owner_user': is_owner_user,
    }

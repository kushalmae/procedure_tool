from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def mission_role_required(*allowed_roles):
    """Require the user to have one of the allowed roles on the current mission.

    Usage:
        @mission_role_required('OPERATOR', 'ADMIN')
        def my_view(request, mission_slug, ...):
            ...

    Superusers always pass. Unauthenticated users are redirected to login.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return redirect(f'{login_url}?next={request.get_full_path()}')

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            membership = getattr(request, 'mission_membership', None)
            if membership and membership.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to perform this action.')
            mission = getattr(request, 'mission', None)
            if mission:
                from django.urls import reverse
                return redirect(reverse('dashboard', kwargs={'mission_slug': mission.slug}))
            return redirect('mission_selector')

        return _wrapped
    return decorator

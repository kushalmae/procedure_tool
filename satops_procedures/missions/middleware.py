from django.http import Http404
from django.shortcuts import redirect

from .models import Mission, MissionMembership


class MissionContextMiddleware:
    """Resolve the current mission from the URL slug and attach to request."""

    MISSION_EXEMPT_PREFIXES = (
        '/admin/',
        '/login/',
        '/logout/',
        '/static/',
        '/favicon',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.mission = None
        request.mission_membership = None

        path = request.path_info

        if path == '/' or any(path.startswith(p) for p in self.MISSION_EXEMPT_PREFIXES):
            return self.get_response(request)

        if path.startswith('/m/'):
            parts = path.split('/')
            if len(parts) >= 3 and parts[2]:
                slug = parts[2]
                try:
                    mission = Mission.objects.get(slug=slug, is_active=True)
                except Mission.DoesNotExist as err:
                    raise Http404(f"Mission '{slug}' not found.") from err

                request.mission = mission

                if request.user.is_authenticated and not request.user.is_superuser:
                    try:
                        request.mission_membership = MissionMembership.objects.get(
                            user=request.user, mission=mission,
                        )
                    except MissionMembership.DoesNotExist:
                        return redirect('mission_selector')
                elif request.user.is_superuser:
                    request.mission_membership = MissionMembership(
                        user=request.user, mission=mission, role=MissionMembership.ROLE_ADMIN,
                    )

        return self.get_response(request)

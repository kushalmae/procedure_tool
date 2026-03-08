from .models import Mission, MissionMembership


def mission_context(request):
    ctx = {
        'current_mission': getattr(request, 'mission', None),
        'mission_membership': getattr(request, 'mission_membership', None),
    }

    if request.user.is_authenticated:
        if request.user.is_superuser:
            ctx['user_missions'] = Mission.objects.filter(is_active=True)
        else:
            member_ids = MissionMembership.objects.filter(
                user=request.user,
            ).values_list('mission_id', flat=True)
            ctx['user_missions'] = Mission.objects.filter(
                pk__in=member_ids, is_active=True,
            )
    else:
        ctx['user_missions'] = Mission.objects.none()

    return ctx

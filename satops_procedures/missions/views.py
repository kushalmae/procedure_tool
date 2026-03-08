from django.shortcuts import redirect, render

from .models import Mission, MissionMembership


def mission_selector(request):
    """Landing page: show missions the user has access to."""
    missions = Mission.objects.filter(is_active=True)
    if request.user.is_authenticated and not request.user.is_superuser:
        member_ids = MissionMembership.objects.filter(
            user=request.user,
        ).values_list('mission_id', flat=True)
        missions = missions.filter(pk__in=member_ids)

    if missions.count() == 1:
        return redirect('dashboard', mission_slug=missions.first().slug)

    return render(request, 'missions/mission_selector.html', {
        'missions': missions,
    })

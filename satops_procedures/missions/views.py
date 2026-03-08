from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.text import slugify

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


@login_required
def mission_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#3B82F6').strip()

        if not name:
            return render(request, 'missions/mission_create.html', {
                'error': 'Mission name is required.',
                'form_name': name,
                'form_description': description,
                'form_color': color,
            })

        slug = slugify(name)
        if not slug:
            return render(request, 'missions/mission_create.html', {
                'error': 'Could not generate a valid slug from the mission name.',
                'form_name': name,
                'form_description': description,
                'form_color': color,
            })

        if Mission.objects.filter(slug=slug).exists():
            return render(request, 'missions/mission_create.html', {
                'error': f'A mission with the slug "{slug}" already exists. Choose a different name.',
                'form_name': name,
                'form_description': description,
                'form_color': color,
            })

        mission = Mission.objects.create(
            name=name,
            slug=slug,
            description=description,
            color=color,
        )
        MissionMembership.objects.create(
            user=request.user,
            mission=mission,
            role=MissionMembership.ROLE_ADMIN,
        )
        messages.success(request, f'Mission "{mission.name}" created successfully.')
        return redirect('dashboard', mission_slug=mission.slug)

    return render(request, 'missions/mission_create.html', {
        'form_color': '#3B82F6',
    })

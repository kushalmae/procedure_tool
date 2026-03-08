from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .decorators import mission_role_required
from .models import MissionMembership

User = get_user_model()


@mission_role_required('ADMIN')
def mission_settings(request, mission_slug):
    mission = request.mission

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'archive':
            mission.is_active = False
            mission.save()
            messages.success(request, f'Mission "{mission.name}" has been archived.')
            return redirect('mission_selector')

        mission.name = request.POST.get('name', mission.name).strip()
        mission.description = request.POST.get('description', '').strip()
        mission.color = request.POST.get('color', mission.color).strip()
        mission.is_sandbox = request.POST.get('is_sandbox') == 'on'
        mission.save()
        messages.success(request, 'Mission settings updated.')
        return redirect(reverse('mission_settings', kwargs={'mission_slug': mission.slug}))

    return render(request, 'missions/mission_settings.html', {
        'mission': mission,
    })


@mission_role_required('ADMIN')
def mission_members(request, mission_slug):
    mission = request.mission
    memberships = MissionMembership.objects.filter(mission=mission).select_related('user').order_by('user__username')

    return render(request, 'missions/mission_members.html', {
        'mission': mission,
        'memberships': memberships,
        'role_choices': MissionMembership.ROLE_CHOICES,
    })


@mission_role_required('ADMIN')
def mission_member_add(request, mission_slug):
    mission = request.mission

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', MissionMembership.ROLE_OPERATOR)
        user = get_object_or_404(User, pk=user_id)

        if MissionMembership.objects.filter(user=user, mission=mission).exists():
            messages.error(request, f'{user.get_username()} is already a member of this mission.')
        else:
            MissionMembership.objects.create(user=user, mission=mission, role=role)
            messages.success(request, f'{user.get_username()} added as {dict(MissionMembership.ROLE_CHOICES).get(role, role)}.')

        return redirect(reverse('mission_members', kwargs={'mission_slug': mission.slug}))

    existing_user_ids = MissionMembership.objects.filter(mission=mission).values_list('user_id', flat=True)
    available_users = User.objects.exclude(pk__in=existing_user_ids).order_by('username')

    return render(request, 'missions/mission_member_add.html', {
        'mission': mission,
        'available_users': available_users,
        'role_choices': MissionMembership.ROLE_CHOICES,
    })


@mission_role_required('ADMIN')
@require_POST
def mission_member_role(request, mission_slug, membership_id):
    mission = request.mission
    membership = get_object_or_404(MissionMembership, pk=membership_id, mission=mission)

    if membership.user == request.user:
        messages.error(request, 'You cannot change your own role.')
    else:
        new_role = request.POST.get('role')
        valid_roles = dict(MissionMembership.ROLE_CHOICES)
        if new_role in valid_roles:
            membership.role = new_role
            membership.save()
            messages.success(request, f'Role for {membership.user.get_username()} changed to {valid_roles[new_role]}.')
        else:
            messages.error(request, 'Invalid role.')

    return redirect(reverse('mission_members', kwargs={'mission_slug': mission.slug}))


@mission_role_required('ADMIN')
@require_POST
def mission_member_remove(request, mission_slug, membership_id):
    mission = request.mission
    membership = get_object_or_404(MissionMembership, pk=membership_id, mission=mission)

    if membership.user == request.user:
        messages.error(request, 'You cannot remove yourself from the mission.')
    else:
        username = membership.user.get_username()
        membership.delete()
        messages.success(request, f'{username} has been removed from the mission.')

    return redirect(reverse('mission_members', kwargs={'mission_slug': mission.slug}))

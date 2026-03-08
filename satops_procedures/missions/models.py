from django.conf import settings
from django.db import models


class Mission(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text='Hex color for UI badge (e.g. #3B82F6)',
    )
    is_sandbox = models.BooleanField(
        default=False,
        help_text='Sandbox missions are for testing and training.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MissionMembership(models.Model):
    ROLE_VIEWER = 'VIEWER'
    ROLE_OPERATOR = 'OPERATOR'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [
        (ROLE_VIEWER, 'Viewer'),
        (ROLE_OPERATOR, 'Operator'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_memberships',
    )
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_OPERATOR,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'mission')
        ordering = ['mission', 'user']

    def __str__(self):
        return f"{self.user} — {self.mission} ({self.get_role_display()})"

    @property
    def can_edit(self):
        return self.role in (self.ROLE_OPERATOR, self.ROLE_ADMIN)

    @property
    def can_admin(self):
        return self.role == self.ROLE_ADMIN


class DashboardLayout(models.Model):
    """Per-user, per-mission dashboard widget configuration stored as JSON."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_layouts',
    )
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='dashboard_layouts',
    )
    layout_json = models.JSONField(
        default=list,
        help_text='List of {widget, enabled, order} dicts',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'mission')

    def __str__(self):
        return f"Dashboard layout: {self.user} @ {self.mission}"

from django.contrib import admin

from .models import Mission, MissionMembership


class MissionMembershipInline(admin.TabularInline):
    model = MissionMembership
    extra = 1


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_sandbox', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MissionMembershipInline]


@admin.register(MissionMembership)
class MissionMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'role', 'joined_at')
    list_filter = ('mission', 'role')

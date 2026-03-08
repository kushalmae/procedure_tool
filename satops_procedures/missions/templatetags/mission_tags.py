from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def murl(context, url_name, *args, **kwargs):
    """Reverse a URL and auto-inject the current mission slug."""
    request = context.get('request')
    mission = getattr(request, 'mission', None) if request else context.get('current_mission')
    if mission and 'mission_slug' not in kwargs:
        kwargs['mission_slug'] = mission.slug
    return reverse(url_name, args=args, kwargs=kwargs)

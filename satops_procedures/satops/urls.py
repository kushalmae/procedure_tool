from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import TemplateView

mission_prefixed = [
    path('', include('procedures.urls')),
    path('scribe/', include('scribe.urls')),
    path('handbook/', include('handbook.urls')),
    path('fdir/', include('fdir.urls')),
    path('anomalies/', include('anomalies.urls')),
    path('cmdtlm/', include('cmdtlm.urls')),
    path('references/', include('references.urls')),
    path('requests/', include('smerequests.urls')),
    path('reports/', include('reports.urls')),
    path('audit/', include('auditlog.urls')),
    path('settings/', include('missions.admin_urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('homepage/', TemplateView.as_view(template_name='homepage.html'), name='homepage'),
    path('', include('missions.urls')),
    path('m/<slug:mission_slug>/', include(mission_prefixed)),
]

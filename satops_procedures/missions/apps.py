import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'missions'

    def ready(self):
        from django.conf import settings
        static_root = settings.STATIC_ROOT
        admin_css = static_root / 'admin' / 'css' if static_root else None
        if admin_css and not admin_css.exists():
            try:
                from django.core.management import call_command
                call_command('collectstatic', '--noinput', verbosity=0)
                logger.info('Auto-ran collectstatic (admin assets were missing).')
            except Exception:
                logger.warning(
                    'Static files have not been collected. '
                    'Run "python manage.py collectstatic" to fix admin styling.'
                )


from django.apps import AppConfig


class ForensicAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Forensic_App'

    def ready(self):
        import Forensic_App.signals

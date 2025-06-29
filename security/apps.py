from django.apps import AppConfig

class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security'
    
    def ready(self):
        import security.signals  # Import signals to connect them

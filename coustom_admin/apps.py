from django.apps import AppConfig


class CoustomAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coustom_admin'
    
    def ready(self):
        # Import signals to register them
        import coustom_admin.signals

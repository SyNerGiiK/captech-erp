from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "ERP - Core"

    def ready(self):
        from . import signals  # connecte les signaux
        from . import roles    # crée/maj des groupes par post_migrate
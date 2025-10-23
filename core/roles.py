from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

GROUPS = {
    "COMPANY_ADMIN": {
        "models": {
            "customer": ["add","change","delete","view"],
            "quote": ["add","change","delete","view"],
            "quoteitem": ["add","change","delete","view"],
            "invoice": ["add","change","delete","view"],
            "invoiceitem": ["add","change","delete","view"],
            "ticket": ["add","change","delete","view"],
        }
    },
    "COMPANY_STAFF": {
        "models": {
            "customer": ["add","change","view"],
            "quote": ["add","change","view"],
            "quoteitem": ["add","change","view"],
            "invoice": ["add","change","view"],
            "invoiceitem": ["add","change","view"],
            "ticket": ["add","change","view"],
        }
    },
    "COMPANY_MEMBER": {
        "models": {
            "customer": ["view"],
            "quote": ["view"],
            "quoteitem": ["view"],
            "invoice": ["view"],
            "invoiceitem": ["view"],
            "ticket": ["view"],
        }
    },
    "SUPPORT_READONLY": {
        "models": {
            "customer": ["view"],
            "quote": ["view"],
            "quoteitem": ["view"],
            "invoice": ["view"],
            "invoiceitem": ["view"],
            "ticket": ["view"],
        }
    },
    "SUPPORT_ENGINEER": {
        "models": {
            "customer": ["view","change"],
            "quote": ["view","change"],
            "quoteitem": ["view","change"],
            "invoice": ["view","change"],
            "invoiceitem": ["view","change"],
            "ticket": ["view","change"],
        }
    },
}

@receiver(post_migrate)
def ensure_groups(sender, **kwargs):
    app_label = "core"
    if sender.label != app_label:
        return
    for gname, spec in GROUPS.items():
        g, _ = Group.objects.get_or_create(name=gname)
        for model, perms in spec["models"].items():
            ct = ContentType.objects.get(app_label=app_label, model=model)
            for p in perms:
                codename = f"{p}_{model}"
                try:
                    perm = Permission.objects.get(content_type=ct, codename=codename)
                    g.permissions.add(perm)
                except Permission.DoesNotExist:
                    pass

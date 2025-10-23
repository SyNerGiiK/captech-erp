from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    return d.get(key, [])


@register.simple_tag(takes_context=True)
def nav_active(context, pattern: str, cls="nav-active"):
    req = context.get("request")
    path = (getattr(req, "path", "") or "").rstrip("/")
    return cls if path.startswith(pattern.rstrip("/")) else ""

@register.filter
def priority_badge_class(priority):
    # LOW / MEDIUM / HIGH
    if priority == "HIGH":
        return "bg-danger-50 text-danger-900"
    if priority == "LOW":
        return "bg-success-50 text-success-900"
    return "bg-amber-50 text-amber-900"

@register.filter
def status_head_class(status):
    # pour les en-têtes Kanban
    return {
        "OPEN": "bg-brand-600",
        "IN_PROGRESS": "bg-indigo-600",
        "WAITING": "bg-amber-600",
        "RESOLVED": "bg-success-600",
        "CLOSED": "bg-ink-500",
    }.get(status, "bg-ink-500")
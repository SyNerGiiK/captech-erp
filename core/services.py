from django.db.models import Max
from django.contrib.auth.models import User
from .models import Ticket, Membership, TicketEvent, Quote, Invoice
from django.utils import timezone

def log_event(ticket: Ticket, type_: str, message: str, actor=None):
    TicketEvent.objects.create(ticket=ticket, type=type_, message=message, actor=actor)

def auto_assign(ticket: Ticket):
    from .models import Membership
    managers = Membership.objects.filter(company=ticket.company, role="MANAGER").select_related("user")
    adminz = Membership.objects.filter(company=ticket.company, role="ADMIN").select_related("user")
    manager = managers.first()
    admin = adminz.first()
    target = manager.user if manager else (admin.user if admin else None)
    if target and (ticket.assigned_to.id if ticket.assigned_to else None) != target.id:
        ticket.assigned_to = target
        ticket.save(update_fields=["assigned_to", "updated_at"])
        log_event(ticket, "ASSIGNED", f"Ticket attribué automatiquement à {target}", actor=None)

def next_order(company, status):
    m = Ticket.objects.filter(company=company, status=status).aggregate(m=Max("order"))["m"]
    return (m or 0) + 1

# --- Numérotation Devis/Factures ---
def next_quote_number(company):
    y = timezone.now().year
    prefix = f"DEV-{y}-"
    last = Quote.objects.filter(company=company, number__startswith=prefix).order_by("-number").first()
    seq = int(last.number.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"

def next_invoice_number(company):
    y = timezone.now().year
    prefix = f"FAC-{y}-"
    last = Invoice.objects.filter(company=company, number__startswith=prefix).order_by("-number").first()
    seq = int(last.number.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"

# --- Calculs totaux (HT/TVA/TTC) en centimes ---
from decimal import Decimal, ROUND_HALF_UP

def compute_totals(items):
    """
    items: iterable d'objets avec quantity, unit_price_cents, vat_rate, discount_pct
    Renvoie (subtotal_cents, tax_cents, total_cents)
    """
    subtotal = Decimal("0")
    tax = Decimal("0")
    for it in items:
        q = Decimal(it.quantity)
        unit = Decimal(it.unit_price_cents) / 100
        disc = Decimal(it.discount_pct or 0) / 100
        line_ht = q * unit * (Decimal("1") - disc)
        line_tax = line_ht * Decimal(it.vat_rate or 0) / 100
        subtotal += line_ht
        tax += line_tax
    subtotal_c = int((subtotal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    tax_c = int((tax * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_c = subtotal_c + tax_c
    return subtotal_c, tax_c, total_c

# --- Gating par plan d'abonnement (simple, via Subscription.plan) ---
FEATURES_BY_PLAN = {
    "BASIC": {"tickets": True, "quotes": True, "invoices": False},
    "PRO": {"tickets": True, "quotes": True, "invoices": True},
    "ENTERPRISE": {"tickets": True, "quotes": True, "invoices": True},
}

def feature_enabled(company, feature_key: str) -> bool:
    sub = company.subscriptions.order_by("-created_at").first()
    plan = (sub.plan if sub else "BASIC")
    return FEATURES_BY_PLAN.get(plan, {}).get(feature_key, False)
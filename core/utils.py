from typing import Iterable
from django.conf import settings
from django.core.mail import send_mail as dj_send_mail
from decimal import Decimal

def send_ticket_email(subject: str, body: str, to: Iterable[str]):
    if not to:
        return
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    # En dev: console/email backend → visible dans la console
    dj_send_mail(subject, body, from_email, list(to), fail_silently=True)

def invoice_total(inv):
    """
    Calcule le total TTC d'une facture à partir de ses items.
    S'adapte à quantité/prix/taxe si certains champs n'existent pas.
    """
    # 1) Si la facture possède déjà un champ total, on l'utilise.
    for attr in ("total_ttc", "total", "amount"):
        if hasattr(inv, attr) and getattr(inv, attr) is not None:
            try:
                return Decimal(getattr(inv, attr))
            except Exception:
                pass

    # 2) Sinon on somme les lignes.
    total = Decimal("0.00")
    # items = relation ManyToOne nommée "items" (d'après ton message d'erreur)
    try:
        items = inv.items.all()
    except Exception:
        items = []

    for it in items:
        qty = getattr(it, "quantity", getattr(it, "qty", 1)) or 1
        unit = getattr(it, "unit_price", getattr(it, "price", Decimal("0.00"))) or Decimal("0.00")
        # taux TVA en %, optionnel
        rate = getattr(it, "tax_rate", getattr(it, "vat_rate", 0)) or 0
        rate = Decimal(str(rate)) / Decimal("100") if rate else Decimal("0")
        line = (Decimal(qty) * Decimal(unit) * (Decimal("1.00") + rate))
        total += line.quantize(Decimal("0.01"))
    return total
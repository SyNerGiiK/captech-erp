# core/accounting.py
from decimal import Decimal
from django.utils import timezone
from .models import LegalThresholds

# Taux URSSAF 2025 (Entreprendre.Service-Public, 19/09/2025)  :contentReference[oaicite:10]{index=10}
URSSAF_RATES = {
    "VENTES": Decimal("0.123"),        # 12,3%
    "SERVICES_BIC": Decimal("0.212"),  # 21,2%
    "LIB_BNC": Decimal("0.246"),       # 24,6%
    "LIB_CIPAV": Decimal("0.232"),     # 23,2%
}

URSSAF_RATES_LIB = {
    "VENTES": "12,3 %",
    "SERVICES_BIC": "21,2 %",
    "LIB_BNC": "24,6 %",
    "LIB_CIPAV": "23,2 %",
}

def get_thresholds(year=None):
    year = year or timezone.now().year
    obj = LegalThresholds.objects.filter(year=year).first()
    if obj:
        return obj
    # fallback : crée avec défauts (sécurise l’usage)
    return LegalThresholds.objects.create(year=year)

def compute_contributions(activity_kind, amount):
    rate = URSSAF_RATES.get(activity_kind, Decimal("0.00"))
    return (amount * rate).quantize(Decimal("0.01")), URSSAF_RATES_LIB.get(activity_kind, "-")

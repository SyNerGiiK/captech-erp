from django.db import models
from django.utils import timezone
from decimal import Decimal

class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Company(Timestamped):
    name = models.CharField(max_length=200)
    siret = models.CharField(max_length=14, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    def __str__(self):
        return self.name
    LEGAL_STATUS = [
        ("MICRO", "Micro-entreprise"),
        ("EI_REEL", "Entreprise individuelle - régime réel"),
        ("EURL_IS", "EURL/SARL à l'IS (gérant TNS)"),
        ("SASU_IS", "SASU/SAS à l'IS (assimilé salarié)"),
    ]
    URSSAF_FREQ = [("MENSUEL", "Mensuel"), ("TRIMESTRIEL", "Trimestriel")]
    ACTIVITY_KIND = [
        ("VENTES", "Vente de marchandises / hébergement (BIC)"),
        ("SERVICES_BIC", "Prestations de services (BIC)"),
        ("LIB_BNC", "Libéral non réglementé (BNC)"),
        ("LIB_CIPAV", "Libéral réglementé (CIPAV)"),
    ]

    legal_status = models.CharField(max_length=20, choices=LEGAL_STATUS, default="MICRO")
    urssaf_frequency = models.CharField(max_length=12, choices=URSSAF_FREQ, default="TRIMESTRIEL")
    activity_kind = models.CharField(max_length=20, choices=ACTIVITY_KIND, default="SERVICES_BIC")
    tva_franchise = models.BooleanField(default=True)

    # utile pour l’affichage
    def display_status(self):
        return dict(self.LEGAL_STATUS).get(self.legal_status, self.legal_status)

class TurnoverEntry(models.Model):
    """Saisie de CA par période (complète l’agrégation par factures)."""
    SOURCE = [
        ("MANUEL", "Saisie manuelle"),
        ("INVOICE", "Factures"),
        ("IMPORT", "Import CSV"),
    ]
    company = models.ForeignKey(Company, related_name="turnover_entries", on_delete=models.CASCADE)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    source = models.CharField(max_length=10, choices=SOURCE, default="MANUEL")

    class Meta:
        ordering = ["-period_start"]
        unique_together = [("company", "period_start", "period_end", "source")]

class LegalThresholds(models.Model):
    """Seuils annuels, éditables si la loi change (par an = indépendants)."""
    year = models.PositiveIntegerField()
    # Plafonds micro (Bercy 2023-2025)
    micro_cap_sales = models.PositiveIntegerField(default=188700)   # €  :contentReference[oaicite:4]{index=4}
    micro_cap_services = models.PositiveIntegerField(default=77700) # €  :contentReference[oaicite:5]{index=5}
    # Franchise TVA (Service-Public 2025, mesure 25k € suspendue fin 2025)
    vat_base_sales = models.PositiveIntegerField(default=85000)           # €  :contentReference[oaicite:6]{index=6}
    vat_base_sales_tol = models.PositiveIntegerField(default=93500)       # €  :contentReference[oaicite:7]{index=7}
    vat_base_services = models.PositiveIntegerField(default=37500)        # €  :contentReference[oaicite:8]{index=8}
    vat_base_services_tol = models.PositiveIntegerField(default=41250)    # €  :contentReference[oaicite:9]{index=9}

    class Meta:
        unique_together = [("year",)]
class Membership(Timestamped):
    ROLE_CHOICES = [("ADMIN","Admin"),("MANAGER","Manager"),("MEMBER","Member")]
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="MEMBER")
    
    class Meta:
        unique_together = ("user", "company")
        
    def __str__(self):
        return f"{self.user} @ {self.company} ({self.role})"

class Ticket(Timestamped):
    STATUS = [("OPEN","Ouvert"),("IN_PROGRESS","En cours"),("WAITING","En attente"),("RESOLVED","Résolu"),("CLOSED","Fermé")]
    PRIORITY = [("LOW","Basse"),("MEDIUM","Moyenne"),("HIGH","Haute")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="tickets")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="OPEN")
    priority = models.CharField(max_length=10, choices=PRIORITY, default="MEDIUM")
    created_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets_created")
    assigned_to = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets_assigned")
    order = models.PositiveIntegerField(default=0, db_index=True)
    
    def __str__(self):
        return f"[{self.company}] {self.title}"
    
    class Meta:
        ordering = ("order", "-created_at")
    
    
        
class Subscription(Timestamped):
    PLAN = [("BASIC","Basic"),("PRO","Pro"),("ENTERPRISE","Enterprise")]
    STATUS = [("ACTIVE","Active"),("CANCELLED","Annulée"),("PAST_DUE","En retard")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.CharField(max_length=20, choices=PLAN, default="BASIC")
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")


class ServiceCheck(Timestamped):
    name = models.CharField(max_length=100)
    url = models.URLField()
    ok = models.BooleanField(default=True)
    last_status = models.IntegerField(null=True, blank=True)
    last_latency_ms = models.IntegerField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"{self.name} ({'OK' if self.ok else 'DOWN'})"

class SystemLog(Timestamped):
    LEVEL = [("INFO","Info"),("WARN","Warn"),("ERROR","Error")]
    level = models.CharField(max_length=10, choices=LEVEL, default="INFO")
    source = models.CharField(max_length=100)
    message = models.TextField()
    data = models.JSONField(null=True, blank=True)

# --- NOUVEAU : commentaires & pièces jointes ---

class TicketComment(Timestamped):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)
    message = models.TextField()
    def __str__(self):
        return f"Comment #{self.pk} on {self.ticket_id}"

class TicketAttachment(Timestamped):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to="attachments/")
    def __str__(self):
        return f"Attachment #{self.pk} on {self.ticket_id}"
    
# --- Historique d’activité du ticket ---

class TicketEvent(Timestamped):
    TYPE = [
        ("CREATED", "Création"),
        ("STATUS_CHANGED", "Changement de statut"),
        ("PRIORITY_CHANGED", "Changement de priorité"),
        ("ASSIGNED", "Attribution"),
        ("COMMENT_ADDED", "Commentaire ajouté"),
        ("ATTACHMENT_ADDED", "Pièce jointe ajoutée"),
    ]
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=32, choices=TYPE)
    message = models.TextField()
    actor = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"[{self.ticket_id}] {self.type} - {self.created_at:%Y-%m-%d %H:%M}"
    
# --- Clients (tiers / destinataires) ---
class Customer(models.Model):
    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    billing_address = models.TextField(blank=True)
    vat_number = models.CharField(max_length=64, blank=True)  # FR: FRxx..., inter-UE
    siret = models.CharField(max_length=14, blank=True)       # FR spécifique
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name}"

# --- Devis ---
class Quote(models.Model):
    STATUS = [
        ("DRAFT","Brouillon"),
        ("SENT","Envoyé"),
        ("ACCEPTED","Accepté"),
        ("DECLINED","Refusé"),
        ("EXPIRED","Expiré"),
        ("CANCELLED","Annulé"),
    ]
    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="quotes")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotes")
    number = models.CharField(max_length=50)  # unicité par company + année
    issue_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    notes = models.TextField(blank=True)
    currency = models.CharField(max_length=10, default="EUR")
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)
    pdf = models.FileField(upload_to="quotes/", null=True, blank=True)

    class Meta:
        unique_together = ("company", "number")

    def __str__(self): return f"{self.number} - {self.customer}"

class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price_cents = models.PositiveIntegerField()  # prix HT en centimes
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=20)  # %
    discount_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0)  # % remise

# --- Factures (plus riche que ta version initiale) ---
class Invoice(models.Model):
    STATUS = [("DRAFT","Brouillon"),("ISSUED","Émise"),("PAID","Payée"),("OVERDUE","En retard"),("CANCELLED","Annulée")]
    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="invoices")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices", null=True, blank=True)
    number = models.CharField(max_length=50)
    issue_date = models.DateField(default=timezone.now)
    due_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    currency = models.CharField(max_length=10, default="EUR")
    notes = models.TextField(blank=True)
    pdf = models.FileField(upload_to="invoices/", null=True, blank=True)
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("company", "number")

    def __str__(self): return self.number

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price_cents = models.PositiveIntegerField()  # HT en centimes
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=20)
    discount_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0)

# --- Accès support avec consentement (grant) ---
class SupportAccessGrant(models.Model):
    SCOPE = [("TICKETS","Tickets"),("BILLING","Facturation"),("ALL","Tout")]
    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="support_grants")
    granted_to = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="support_grants")
    granted_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, related_name="support_grants_by")
    scope = models.CharField(max_length=20, choices=SCOPE, default="ALL")
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return self.active and self.expires_at >= timezone.now()
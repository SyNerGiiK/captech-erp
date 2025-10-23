from django.contrib import admin
from django.utils import timezone
from . import models

def companies_user_can_access(user):
    from django.db.models import Q
    qs = models.Company.objects.none()
    if user.is_superuser:
        # Mode strict: on n'affiche QUE les companies avec grant actif
        return models.Company.objects.filter(
            support_grants__granted_to=user,
            support_grants__active=True,
            support_grants__expires_at__gte=timezone.now()
        ).distinct()
    # Membres: leur propre company
    return models.Company.objects.filter(memberships__user=user).distinct()

class CompanyBoundAdmin(admin.ModelAdmin):
    """
    Restreint la visibilité aux companies accessibles.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_staff:
            allowed = companies_user_can_access(request.user)
            # si superuser sans grant, tu peux autoriser tout en commentant la ligne suivante
            return qs.filter(company__in=allowed) if qs.model != models.Company else allowed
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.related_model and hasattr(db_field.related_model, "company"):
            allowed = companies_user_can_access(request.user)
            kwargs["queryset"] = db_field.related_model.objects.filter(company__in=allowed)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(models.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name","email","active","created_at")
    search_fields = ("name","email","siret")
    list_filter = ("active",)

@admin.register(models.Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user","company","role","created_at")
    list_filter = ("role","company")
    search_fields = ("user__username","company__name")

class TicketCommentInline(admin.TabularInline): model = models.TicketComment; extra = 0
class TicketAttachmentInline(admin.TabularInline): model = models.TicketAttachment; extra = 0
class TicketEventInline(admin.TabularInline):
    model = models.TicketEvent; extra = 0
    can_delete = False
    readonly_fields = ("type","message","actor","created_at","updated_at")

@admin.register(models.Ticket)
class TicketAdmin(CompanyBoundAdmin):
    list_display = ("title","company","status","priority","assigned_to","created_at")
    list_filter = ("status","priority","company")
    search_fields = ("title","description")
    autocomplete_fields = ("company","created_by","assigned_to")
    inlines = [TicketEventInline, TicketCommentInline, TicketAttachmentInline]
    actions = ["mark_resolved","mark_closed"]
    def mark_resolved(self, request, queryset): queryset.update(status="RESOLVED")
    def mark_closed(self, request, queryset): queryset.update(status="CLOSED")

@admin.register(models.Customer)
class CustomerAdmin(CompanyBoundAdmin):
    list_display = ("name","company","email","phone","active","created_at")
    search_fields = ("name","email","siret")
    list_filter = ("company","active")

class QuoteItemInline(admin.TabularInline): model = models.QuoteItem; extra = 0
@admin.register(models.Quote)
class QuoteAdmin(CompanyBoundAdmin):
    list_display = ("number","company","customer","status","issue_date","valid_until")
    list_filter = ("status","company")
    search_fields = ("number","customer__name")
    inlines = [QuoteItemInline]

class InvoiceItemInline(admin.TabularInline): model = models.InvoiceItem; extra = 0
@admin.register(models.Invoice)
class InvoiceAdmin(CompanyBoundAdmin):
    list_display = ("number","company","customer","status","issue_date","due_at")
    list_filter = ("status","company")
    search_fields = ("number","customer__name")
    inlines = [InvoiceItemInline]

@admin.register(models.SupportAccessGrant)
class SupportGrantAdmin(admin.ModelAdmin):
    list_display = ("company","granted_to","scope","active","expires_at","created_at")
    list_filter = ("active","scope","company")
    search_fields = ("company__name","granted_to__username")

@admin.register(models.ServiceCheck)
class ServiceCheckAdmin(admin.ModelAdmin):
    list_display = ("name","url","ok","last_status","last_latency_ms","last_checked_at","updated_at")
    list_filter = ("ok",)
    search_fields = ("name","url")

@admin.register(models.SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("created_at","level","source","message_short")
    list_filter = ("level","source")
    search_fields = ("message","source")

    def message_short(self, obj):
        return (obj.message[:80] + "…") if len(obj.message) > 80 else obj.message
    message_short.short_description = "message"

@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "plan", "status", "period_start", "period_end", "created_at")
    list_filter = ("plan", "status", "company")
    search_fields = ("company__name",)
    
@admin.register(models.TurnoverEntry)
class TurnoverEntryAdmin(admin.ModelAdmin):
    list_display = ("company", "period_start", "period_end", "amount", "source")
    list_filter = ("company", "source")
    date_hierarchy = "period_start"
    search_fields = ("company__name",)

@admin.register(models.LegalThresholds)
class LegalThresholdsAdmin(admin.ModelAdmin):
    list_display = ("year", "micro_cap_sales", "micro_cap_services",
                    "vat_base_sales", "vat_base_sales_tol",
                    "vat_base_services", "vat_base_services_tol")
    list_filter = ("year",)
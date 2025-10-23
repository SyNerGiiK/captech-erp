from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Ticket, TicketComment, TicketAttachment, Membership
from .services import log_event, auto_assign, next_order
from .utils import send_ticket_email

def _company_recipients(ticket: Ticket):
    # envoie aux admins + créateur (s’il a un email)
    emails = set()
    admins = Membership.objects.filter(company=ticket.company, role="ADMIN").select_related("user")
    for m in admins:
        if m.user.email:
            emails.add(m.user.email)
    if ticket.created_by and ticket.created_by.email:
        emails.add(ticket.created_by.email)
    if ticket.assigned_to and ticket.assigned_to.email:
        emails.add(ticket.assigned_to.email)
    return list(emails)

@receiver(post_save, sender=Ticket)
def on_ticket_created(sender, instance: Ticket, created, **kwargs):
    if created:
        # init order si 0
        if not instance.order:
            instance.order = next_order(instance.company, instance.status)
            instance.save(update_fields=["order", "updated_at"])
        log_event(instance, "CREATED", f"Ticket créé: {instance.title}", actor=instance.created_by)
        auto_assign(instance)
        send_ticket_email(
            f"[Ticket #{instance.pk}] Créé - {instance.title}",
            f"Un nouveau ticket a été créé.\n\nStatut: {instance.status}\nPriorité: {instance.priority}\nDescription:\n{instance.description}",
            _company_recipients(instance),
        )
        # auto assign
        auto_assign(instance)
        # email
        send_ticket_email(
            f"[Ticket #{instance.pk}] Créé - {instance.title}",
            f"Un nouveau ticket a été créé.\n\nStatut: {instance.status}\nPriorité: {instance.priority}\nDescription:\n{instance.description}",
            _company_recipients(instance),
        )

@receiver(pre_save, sender=Ticket)
def on_ticket_pre_save(sender, instance: Ticket, **kwargs):
    # stocke l'état précédent pour comparaison en post_save
    if instance.pk:
        old = Ticket.objects.filter(pk=instance.pk).only("status", "priority").first()
        instance._old_status = old.status if old else None
        instance._old_priority = old.priority if old else None
    else:
        instance._old_status = None
        instance._old_priority = None

@receiver(post_save, sender=Ticket)
def on_ticket_updated(sender, instance: Ticket, created, **kwargs):
    if created:
        return
    msgs = []
    if hasattr(instance, "_old_status") and instance._old_status and instance._old_status != instance.status:
        log_event(instance, "STATUS_CHANGED", f"Statut: {instance._old_status} → {instance.status}")
        msgs.append(f"Statut: {instance._old_status} → {instance.status}")
    if hasattr(instance, "_old_priority") and instance._old_priority and instance._old_priority != instance.priority:
        log_event(instance, "PRIORITY_CHANGED", f"Priorité: {instance._old_priority} → {instance.priority}")
        msgs.append(f"Priorité: {instance._old_priority} → {instance.priority}")
    if msgs:
        send_ticket_email(
            f"[Ticket #{instance.pk}] Mise à jour",
            " / ".join(msgs),
            _company_recipients(instance),
        )

@receiver(post_save, sender=TicketComment)
def on_comment(sender, instance: TicketComment, created, **kwargs):
    if created:
        log_event(instance.ticket, "COMMENT_ADDED", f"Commentaire ajouté par {instance.author}: {instance.message[:120]}", actor=instance.author)
        send_ticket_email(
            f"[Ticket #{instance.ticket_id}] Nouveau commentaire",
            f"{instance.author} a commenté:\n\n{instance.message}",
            _company_recipients(instance.ticket),
        )

@receiver(post_save, sender=TicketAttachment)
def on_attachment(sender, instance: TicketAttachment, created, **kwargs):
    if created:
        log_event(instance.ticket, "ATTACHMENT_ADDED", f"Pièce jointe ajoutée: {instance.file.name}", actor=instance.uploaded_by)
        send_ticket_email(
            f"[Ticket #{instance.ticket_id}] Pièce jointe",
            f"{instance.uploaded_by} a ajouté un fichier: {instance.file.name}",
            _company_recipients(instance.ticket),
        )

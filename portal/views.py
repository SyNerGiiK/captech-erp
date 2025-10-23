import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages, auth
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpRequest, HttpResponseRedirect, Http404, JsonResponse, HttpResponse
from django.urls import reverse
from django.db.models import Q, Sum
from django.db import transaction
from django.utils.dateparse import parse_date
from django.forms import inlineformset_factory
from core.accounting import get_thresholds, compute_contributions
from core.models import Membership, Company, Ticket, Customer, Quote, QuoteItem, Invoice, InvoiceItem, TicketEvent, ServiceCheck, SystemLog, TurnoverEntry
from core.services import next_quote_number, next_invoice_number, compute_totals, feature_enabled
from core.pdf import render_pdf_from_template
from core.utils import invoice_total
from .forms import TicketForm, TicketCommentForm, TicketAttachmentForm, TicketStatusForm, SignupForm, QuoteForm, QuoteItemFormSet, InvoiceForm, InvoiceItemFormSet
from datetime import datetime
from decimal import Decimal


def _is_superuser(u): return u.is_superuser

def _require_feature(company, key):
    if not feature_enabled(company, key):
        raise Http404("Fonction non disponible pour votre abonnement")
    
def _user_company(request):
    m = Membership.objects.select_related("company").filter(user=request.user).first()
    return m.company if m else None

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            c = Company.objects.create(name=form.cleaned_data["company_name"], email=form.cleaned_data["email"])
            u = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            Membership.objects.create(user=u, company=c, role="ADMIN")
            # Groupes
            admin_group = Group.objects.get(name="COMPANY_ADMIN")
            u.groups.add(admin_group)
            # connexion
            auth.login(request, u)
            messages.success(request, "Bienvenue ! Entreprise créée.")
            return redirect("portal:dashboard")
    else:
        form = SignupForm()
    return render(request, "portal/signup.html", {"form": form})

@login_required
def dashboard(request):
    company = _user_company(request)
    if not company:
        return render(request, "portal/dashboard.html", {"company": None})

    base = Ticket.objects.filter(company=company)

    stats = {
        "total": base.count(),
        "open": base.filter(status="OPEN").count(),
        "in_progress": base.filter(status="IN_PROGRESS").count(),
        "waiting": base.filter(status="WAITING").count(),
        "resolved": base.filter(status="RESOLVED").count(),
        "closed": base.filter(status="CLOSED").count(),
    }

    # même source que le kanban, tri par created_at décroissant
    recent_tickets = (
        base.select_related("assigned_to")
            .order_by("-created_at")[:8]
    )

    ctx = {
        "company": company,
        "stats": stats,
        "recent_tickets": recent_tickets,
    }
    return render(request, "portal/dashboard.html", ctx)


@login_required
def tickets(request):
    company = _user_company(request)
    if not company:
        return render(request, "portal/tickets.html", {"company": None})

    qs = (
        Ticket.objects
        .filter(company=company)
        .select_related("assigned_to")
        .order_by("-created_at")        # IMPORTANT : pas de filtre implicite
    )

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    priority = (request.GET.get("priority") or "").strip()
    d_from = parse_date(request.GET.get("from") or "")
    d_to = parse_date(request.GET.get("to") or "")

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if d_from:
        qs = qs.filter(created_at__date__gte=d_from)
    if d_to:
        qs = qs.filter(created_at__date__lte=d_to)

    # Pour tes <select> dans le template
    status_choices = Ticket._meta.get_field("status").choices
    priority_choices = Ticket._meta.get_field("priority").choices

    ctx = {
        "company": company,
        "tickets": list(qs),  # force l’éval, utile pour debugger
        "status_choices": status_choices,
        "priority_choices": priority_choices,
    }
    return render(request, "portal/tickets.html", ctx)

@login_required
def ticket_create(request: HttpRequest):
    company = _user_company(request)
    if not company:
        messages.error(request, "Aucune entreprise associée à votre compte. Contactez le support.")
        return HttpResponseRedirect(reverse("portal:dashboard"))

    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.company = company
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, "✅ Ticket créé avec succès.")
            return HttpResponseRedirect(reverse("portal:tickets"))
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = TicketForm()
    return render(request, "portal/ticket_form.html", {"company": company, "form": form})

@login_required
def ticket_detail(request: HttpRequest, pk: int):
    company = _user_company(request)
    if not company:
        messages.error(request, "Aucune entreprise associée à votre compte.")
        return HttpResponseRedirect(reverse("portal:dashboard"))

    try:
        ticket = Ticket.objects.select_related("company", "assigned_to", "created_by").get(pk=pk, company=company)
    except Ticket.DoesNotExist:
        raise Http404("Ticket introuvable")

    status_form = TicketStatusForm(request.POST or None, instance=ticket, prefix="status")
    comment_form = TicketCommentForm(request.POST or None, prefix="comment")
    attachment_form = TicketAttachmentForm(request.POST or None, request.FILES or None, prefix="attach")

    if request.method == "POST":
        if "status-submit" in request.POST and status_form.is_valid():
            status_form.save()
            messages.success(request, "✅ Statut/ Priorité mis à jour.")
            return HttpResponseRedirect(request.path)

        if "comment-submit" in request.POST and comment_form.is_valid():
            c = comment_form.save(commit=False)
            c.ticket = ticket
            c.author = request.user
            c.save()
            messages.success(request, "✅ Commentaire ajouté.")
            return HttpResponseRedirect(request.path)

        if "attach-submit" in request.POST and attachment_form.is_valid():
            a = attachment_form.save(commit=False)
            a.ticket = ticket
            a.uploaded_by = request.user
            a.save()
            messages.success(request, "✅ Pièce jointe envoyée.")
            return HttpResponseRedirect(request.path)

        messages.error(request, "Veuillez corriger les erreurs.")

    ctx = {
        "company": company,
        "ticket": ticket,
        "status_form": status_form,
        "comment_form": comment_form,
        "attachment_form": attachment_form,
        "events": ticket.events.order_by("-created_at"),  # <-- historique
    }
    return render(request, "portal/ticket_detail.html", ctx)

@login_required
def tickets_kanban(request):
    company = _user_company(request)
    if not company:
        messages.error(request, "Aucune entreprise associée à votre compte.")
        return HttpResponseRedirect(reverse("portal:dashboard"))

    move_id = request.GET.get("move")
    to_status = request.GET.get("to")
    VALID = {"OPEN","IN_PROGRESS","WAITING","RESOLVED","CLOSED"}
    if move_id and to_status in VALID:
        try:
            t = Ticket.objects.get(pk=move_id, company=company)
            old = t.status
            if old != to_status:
                t.status = to_status
                t.save(update_fields=["status","updated_at"])
                messages.success(request, f"✅ Ticket #{t.pk}: {old} → {to_status}")
            return HttpResponseRedirect(reverse("portal:tickets_kanban"))
        except Ticket.DoesNotExist:
            messages.error(request, "Ticket introuvable ou non autorisé.")
            return HttpResponseRedirect(reverse("portal:tickets_kanban"))

    cols = {
        "OPEN": Ticket.objects.filter(company=company, status="OPEN").order_by("order", "-created_at"),
        "IN_PROGRESS": Ticket.objects.filter(company=company, status="IN_PROGRESS").order_by("order", "-created_at"),
        "WAITING": Ticket.objects.filter(company=company, status="WAITING").order_by("order", "-created_at"),
        "RESOLVED": Ticket.objects.filter(company=company, status="RESOLVED").order_by("order", "-created_at"),
        "CLOSED": Ticket.objects.filter(company=company, status="CLOSED").order_by("order", "-created_at"),
    }
    columns = [
        ("OPEN", "Ouvert", "bg-sky-600"),
        ("IN_PROGRESS", "En cours", "bg-indigo-600"),
        ("WAITING", "En attente", "bg-amber-600"),
        ("RESOLVED", "Résolu", "bg-emerald-600"),
        ("CLOSED", "Fermé", "bg-slate-600"),
    ]

    # Compteurs et "heat opacity" côté serveur (valeur initiale)
    counts = {k: cols[k].count() for k in cols}
    total = max(1, sum(counts.values()))  # éviter division par zéro
    def heat_class(k):
        r = counts[k] / total
        # plus c’est chargé, plus c’est opaque
        if r == 0:
            return "opacity-50"
        if r <= 0.25:
            return "opacity-70"
        if r <= 0.5:
            return "opacity-80"
        if r <= 0.75:
            return "opacity-90"
        return ""  # plein

    heat = {k: heat_class(k) for k in counts}

    return render(
        request,
        "portal/tickets_kanban.html",
        {"company": company, "cols": cols, "columns": columns, "counts": counts, "total": total, "heat": heat},
    )

@login_required
@require_POST
def tickets_kanban_move(request):
    company = _user_company(request)
    if not company:
        return JsonResponse({"ok": False, "error": "no_company"}, status=403)

    tid = request.POST.get("id")
    to_status = request.POST.get("to")
    VALID = {"OPEN","IN_PROGRESS","WAITING","RESOLVED","CLOSED"}
    if not (tid and to_status in VALID):
        return JsonResponse({"ok": False, "error": "bad_params"}, status=400)

    try:
        t = Ticket.objects.get(pk=tid, company=company)
    except Ticket.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    old = t.status
    if old != to_status:
        t.status = to_status
        t.save(update_fields=["status","updated_at"])  # signaux = events + emails
    return JsonResponse({"ok": True, "id": t.pk, "from": old, "to": to_status})

@user_passes_test(_is_superuser)
def admin_dashboard(request):
    # Compteurs rapides
    total = Ticket.objects.count()
    open_ = Ticket.objects.filter(status="OPEN").count()
    inprog = Ticket.objects.filter(status="IN_PROGRESS").count()
    wait = Ticket.objects.filter(status="WAITING").count()
    res = Ticket.objects.filter(status="RESOLVED").count()
    closed = Ticket.objects.filter(status="CLOSED").count()

    latest_events = TicketEvent.objects.select_related("ticket","actor").order_by("-created_at")[:12]
    checks = ServiceCheck.objects.order_by("-updated_at")[:8]
    logs = SystemLog.objects.order_by("-created_at")[:10]

    ctx = {
        "counts": {"total": total, "open": open_, "inprog": inprog, "wait": wait, "res": res, "closed": closed},
        "latest_events": latest_events,
        "checks": checks,
        "logs": logs,
    }
    return render(request, "portal/admin_dashboard.html", ctx)

@login_required
@require_POST
def tickets_kanban_reorder(request):
    company = _user_company(request)
    if not company:
        return JsonResponse({"ok": False, "error": "no_company"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        # fallback form-encoded
        payload = request.POST

    status = payload.get("status")
    ids = payload.get("ids")
    if isinstance(ids, str):
        # CSV -> liste
        ids = [i for i in ids.split(",") if i.strip()]
    if not status or not isinstance(ids, (list, tuple)):
        return JsonResponse({"ok": False, "error": "bad_params"}, status=400)

    # Vérifie que tous les tickets appartiennent à la company et à la colonne visée
    qs = Ticket.objects.filter(company=company, status=status, pk__in=ids)
    if qs.count() != len(ids):
        return JsonResponse({"ok": False, "error": "mismatch"}, status=400)

    # Persiste l'ordre : 0..n-1 (ou 1..n si tu préfères)
    with transaction.atomic():
        for idx, tid in enumerate(ids):
            Ticket.objects.filter(pk=tid, company=company).update(order=idx)

    return JsonResponse({"ok": True, "count": len(ids)})

@login_required
def quotes(request):
    company = _user_company(request)
    if not company: return render(request, "portal/quotes.html", {"company": None})
    _require_feature(company, "quotes")
    qs = Quote.objects.filter(company=company).select_related("customer").order_by("-issue_date","-id")
    return render(request, "portal/quotes.html", {"company": company, "items": qs})

@login_required
def quote_new(request):
    company = _user_company(request); _require_feature(company, "quotes")
    q = Quote(company=company, number=next_quote_number(company), created_by=request.user)
    if request.method == "POST":
        form = QuoteForm(request.POST, instance=q)
        formset = QuoteItemFormSet(request.POST, instance=q)
        if form.is_valid() and formset.is_valid():
            form.save(); formset.save()
            messages.success(request, "Devis enregistré.")
            return redirect("portal:quotes")
    else:
        form = QuoteForm(instance=q)
        formset = QuoteItemFormSet(instance=q)
    return render(request, "portal/quote_form.html", {"company": company, "form": form, "formset": formset, "obj": q})

@login_required
def quote_edit(request, pk: int):
    company = _user_company(request); _require_feature(company, "quotes")
    q = Quote.objects.filter(company=company, pk=pk).first()
    if not q:
        raise Http404()
    if request.method == "POST":
        form = QuoteForm(request.POST, instance=q)
        formset = QuoteItemFormSet(request.POST, instance=q)
        if form.is_valid() and formset.is_valid():
            form.save(); formset.save()
            messages.success(request, "Devis mis à jour.")
            return redirect("portal:quotes")
    else:
        form = QuoteForm(instance=q)
        formset = QuoteItemFormSet(instance=q)
    return render(request, "portal/quote_form.html", {"company": company, "form": form, "formset": formset, "obj": q})

@login_required
def quote_pdf(request, pk: int):
    company = _user_company(request); _require_feature(company, "quotes")
    q = Quote.objects.select_related("customer","company").prefetch_related("items").filter(company=company, pk=pk).first()
    if not q:
        raise Http404()
    subtotal, tax, total = compute_totals(q.items.all())
    pdf = render_pdf_from_template("pdf/quote.html", {"q": q, "subtotal": subtotal, "tax": tax, "total": total})
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{q.number}.pdf"'
    return resp

# ---- Factures ----
@login_required
def invoices(request):
    company = _user_company(request)
    if not company: return render(request, "portal/invoices.html", {"company": None})
    _require_feature(company, "invoices")
    qs = Invoice.objects.filter(company=company).select_related("customer").order_by("-issue_date","-id")
    return render(request, "portal/invoices.html", {"company": company, "items": qs})

@login_required
def invoice_new(request):
    company = _user_company(request); _require_feature(company, "invoices")
    inv = Invoice(company=company, number=next_invoice_number(company), created_by=request.user)
    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=inv)
        formset = InvoiceItemFormSet(request.POST, instance=inv)
        if form.is_valid() and formset.is_valid():
            form.save(); formset.save()
            messages.success(request, "Facture enregistrée.")
            return redirect("portal:invoices")
    else:
        form = InvoiceForm(instance=inv)
        formset = InvoiceItemFormSet(instance=inv)
    return render(request, "portal/invoice_form.html", {"company": company, "form": form, "formset": formset, "obj": inv})

@login_required
def invoice_edit(request, pk: int):
    company = _user_company(request); _require_feature(company, "invoices")
    inv = Invoice.objects.filter(company=company, pk=pk).first() or Http404()
    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=inv)
        formset = InvoiceItemFormSet(request.POST, instance=inv)
        if form.is_valid() and formset.is_valid():
            form.save(); formset.save()
            messages.success(request, "Facture mise à jour.")
            return redirect("portal:invoices")
    else:
        form = InvoiceForm(instance=inv)
        formset = InvoiceItemFormSet(instance=inv)
    return render(request, "portal/invoice_form.html", {"company": company, "form": form, "formset": formset, "obj": inv})

@login_required
def invoice_pdf(request, pk: int):
    company = _user_company(request); _require_feature(company, "invoices")
    inv = Invoice.objects.select_related("customer","company").prefetch_related("items").filter(company=company, pk=pk).first() or Http404()
    subtotal, tax, total = compute_totals(inv.items.all())
    pdf = render_pdf_from_template("pdf/invoice.html", {"inv": inv, "subtotal": subtotal, "tax": tax, "total": total})
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{inv.number}.pdf"'
    return resp

def _invoices_total_for_period(company, start, end):
    qs = Invoice.objects.filter(
        company=company, issue_date__gte=start, issue_date__lte=end
    ).prefetch_related("items")
    total = Decimal("0.00")
    for inv in qs:
        total += invoice_total(inv)
    return total

@login_required
def accounting_dashboard(request):
    company = _user_company(request)
    if not company:
        raise Http404()

    today = timezone.now().date()
    year = today.year
    th = get_thresholds(year)

    # CA cumulé depuis le 1er janvier (factures émises)
    year_start = today.replace(month=1, day=1)
    inv_sum = _invoices_total_for_period(company, year_start, today)
    # Saisies manuelles éventuelles
    manual_sum = TurnoverEntry.objects.filter(company=company, period_start__gte=year_start, period_end__lte=today)\
                                      .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    ca_ytd = (inv_sum or Decimal("0.00")) + (manual_sum or Decimal("0.00"))

    # Plafonds micro
    micro_cap = th.micro_cap_sales if company.activity_kind == "VENTES" else th.micro_cap_services
    micro_progress = float((ca_ytd / Decimal(micro_cap)) * 100) if micro_cap else 0.0

    # Franchise TVA (selon activité, base + tolérance)
    if company.activity_kind == "VENTES":
        vat_base = th.vat_base_sales
        vat_tol = th.vat_base_sales_tol
    else:
        vat_base = th.vat_base_services
        vat_tol = th.vat_base_services_tol

    # URSSAF – estimation période courante (mensuel/trimestriel)
    if company.urssaf_frequency == "MENSUEL":
        period_start = today.replace(day=1)
    else:
        q = (today.month - 1) // 3
        period_start = today.replace(month=q*3 + 1, day=1)
    period_end = today

    period_ca = _invoices_total_for_period(company, period_start, period_end)

    contrib, rate_label = compute_contributions(company.activity_kind, period_ca)

    ctx = {
        "company": company,
        "year": year,
        "ca_ytd": ca_ytd,
        "micro_cap": micro_cap,
        "micro_progress": round(micro_progress, 2),
        "vat_base": vat_base,
        "vat_tol": vat_tol,
        "period_start": period_start,
        "period_end": period_end,
        "period_ca": period_ca,
        "contrib": contrib,
        "urssaf_rate_label": rate_label,
    }

    return render(request, "portal/accounting/dashboard.html", ctx)

@login_required
def urssaf_pdf(request):
    """Génère un PDF récapitulatif URSSAF pour la période courante."""
    company = _user_company(request)
    if not company:
        raise Http404()

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from io import BytesIO
    from django.utils import timezone

    today = timezone.now().date()
    if company.urssaf_frequency == "MENSUEL":
        period_start = today.replace(day=1)
    else:
        q = (today.month - 1) // 3
        period_start = today.replace(month=q*3 + 1, day=1)
    period_end = today

    period_ca = _invoices_total_for_period(company, period_start, period_end)

    contrib, rate_label = compute_contributions(company.activity_kind, period_ca)

    template = get_template("pdf/urssaf_summary.html")
    html = template.render({
        "company": company, "period_start": period_start, "period_end": period_end,
        "period_ca": period_ca, "contrib": contrib, "urssaf_rate_label": rate_label,
    })
    out = BytesIO()
    pisa.CreatePDF(html, dest=out)
    resp = HttpResponse(out.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = "inline; filename=urssaf_%s_%s.pdf" % (period_start.isoformat(), period_end.isoformat())
    return resp
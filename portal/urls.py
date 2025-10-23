from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.dashboard, name="dashboard"),
    path("tickets/", views.tickets, name="tickets"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/kanban/", views.tickets_kanban, name="tickets_kanban"),
    path("tickets/kanban/move/", views.tickets_kanban_move, name="tickets_kanban_move"),
    path("tickets/kanban/reorder/", views.tickets_kanban_reorder, name="tickets_kanban_reorder"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("quotes/", views.quotes, name="quotes"),
    path("quotes/new/", views.quote_new, name="quote_new"),
    path("quotes/<int:pk>/edit/", views.quote_edit, name="quote_edit"),
    path("quotes/<int:pk>/pdf/", views.quote_pdf, name="quote_pdf"),
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/new/", views.invoice_new, name="invoice_new"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("accounting/", views.accounting_dashboard, name="accounting"),
    path("accounting/urssaf/pdf/", views.urssaf_pdf, name="urssaf_pdf"),
]

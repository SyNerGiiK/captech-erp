from django import forms
from django.contrib.auth.models import User
from core.models import Company, Customer, Quote, QuoteItem, Invoice, InvoiceItem, Ticket, TicketComment, TicketAttachment
from django.forms import ModelForm
from django.forms import modelform_factory
from django.forms import inlineformset_factory

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre du ticket"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 6, "placeholder": "Décrivez le problème…"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {"title": "Titre", "description": "Description", "priority": "Priorité"}

class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Ajouter un commentaire…"})
        }
        labels = {"message": "Commentaire"}

class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ["file"]
        widgets = {"file": forms.FileInput(attrs={"class": "form-control"})}
        labels = {"file": "Fichier"}

class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "priority"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {"status": "Statut", "priority": "Priorité"}

class SignupForm(forms.Form):
    company_name = forms.CharField(max_length=200, label="Nom de l'entreprise")
    email = forms.EmailField(label="Email")
    username = forms.CharField(max_length=150, label="Identifiant")
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Identifiant déjà utilisé")
        return u
    
class QuoteForm(ModelForm):
    class Meta:
        model = Quote
        fields = ["customer", "issue_date", "valid_until", "status", "notes", "currency"]

class QuoteItemForm(ModelForm):
    class Meta:
        model = QuoteItem
        fields = ["description", "quantity", "unit_price_cents", "vat_rate", "discount_pct"]

QuoteItemFormSet = inlineformset_factory(Quote, QuoteItem, form=QuoteItemForm, extra=2, can_delete=True)

class InvoiceForm(ModelForm):
    class Meta:
        model = Invoice
        fields = ["customer", "issue_date", "due_at", "status", "notes", "currency"]

class InvoiceItemForm(ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["description", "quantity", "unit_price_cents", "vat_rate", "discount_pct"]

InvoiceItemFormSet = inlineformset_factory(Invoice, InvoiceItem, form=InvoiceItemForm, extra=2, can_delete=True)
from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa

def render_pdf_from_template(template_name: str, context: dict) -> bytes:
    html = render_to_string(template_name, context)
    result = BytesIO()
    pisa.CreatePDF(html, dest=result, encoding='utf-8')
    return result.getvalue()

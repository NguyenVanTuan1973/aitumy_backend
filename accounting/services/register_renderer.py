from jinja2 import Template
from datetime import date


def render_register(
    template_text,
    organization,
    rows,
    total,
    year
):

    template = Template(template_text)

    context = {
        "company_name": organization.name or "",
        "company_address": organization.address or "",
        "business_location": organization.address or "",
        "tax_year": year,

        "rows": rows,
        "total": total,

        "report_day": date.today().day,
        "report_month": date.today().month,
        "report_year": date.today().year,

        "owner_name": organization.name,
    }

    return template.render(**context)
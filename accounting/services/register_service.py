from .register_engine import RegisterEngine
from .export.base_pdf_renderer import BasePDFRenderer


def generate_register_pdf(
    organization,
    rows,
    form_code,
    year,
    file_path
):

    register = RegisterEngine.get_register(form_code)

    renderer = BasePDFRenderer(file_path)

    elements = register.build_pdf(
        renderer=renderer,
        organization=organization,
        rows=rows,
        year=year
    )

    pdf_path = renderer.build(elements)

    return pdf_path
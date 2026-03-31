from .register_engine import RegisterEngine
from .export.base_pdf_renderer import BasePDFRenderer


def generate_register_pdf(
    organization,
    rows,
    form_code,
    year,
    file_path
):

    # lấy register tương ứng
    register = RegisterEngine.get_register(form_code)

    # filter dữ liệu
    rows = register.filter_rows(rows)

    # khởi tạo renderer
    renderer = BasePDFRenderer(file_path)

    # register build layout
    elements = register.build_pdf(
        renderer=renderer,
        organization=organization,
        rows=rows,
        year=year
    )

    # render PDF
    pdf_path = renderer.build(elements)

    return pdf_path
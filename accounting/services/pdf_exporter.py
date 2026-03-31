# from .export.base_pdf_renderer import BasePDFRenderer
#
#
# def export_register_pdf(register, rows, company):
#
#     renderer = BasePDFRenderer(
#         f"media/register_{register.__class__.__name__}.pdf"
#     )
#
#     rows = register.filter_rows(rows)
#
#     table_data = register.build_rows(rows)
#
#     elements = []
#
#     elements += renderer.build_header(
#         company["name"],
#         company["address"]
#     )
#
#     elements += renderer.build_title(register.title)
#
#     elements.append(renderer.build_table(table_data))
#
#     return renderer.render(elements)
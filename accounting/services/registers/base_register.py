class BaseRegister:

    title = ""
    form_code = ""

    def filter_rows(self, rows):
        return rows

    def build_pdf(self, renderer, organization, rows):
        raise NotImplementedError
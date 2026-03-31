# accounting/utils/parser.py


def parse_accounting_code(code):
    """
    Convert '111,511' -> ('111','511')
    """
    if not code:
        return None, None

    parts = str(code).split(",")

    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    return None, None


def build_doc_register(regulation_source, code):
    """
    Build doc_register used in sheet
    """
    return f"{regulation_source}_{code}"
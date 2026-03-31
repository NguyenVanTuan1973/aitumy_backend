def ensure_base_tabs(self, spreadsheet_id):
    tabs = [
        "opening_balances",
        "documents_metadata",
        "data_source",
        "inventory_opening",
    ]

    for tab in tabs:
        self.ensure_sheet_exists(spreadsheet_id, tab)
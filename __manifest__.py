{
    "name": "Due Invoice Report",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    'author':'James Oginga',
    "summary": "Print due invoices for a selected partner.",
    "depends": ["base", "mail", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/due_invoice_wizard_view.xml",
        "report/due_invoice_template.xml",
        "report/due_invoice_report.xml",
        "data/email_templates.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": False,
}

{
    "name": "Invoice Project Title",
    "version": "1.4",
    "summary": "Adds Project Title to Invoice, shows it on print.",
    "description": "Adds a 'Project Title' field to the Invoice form and displays it on the printed invoice report",
    "category": "Accounting",
    'author': 'MOB - Ifeanyi Nneji',
    'website': 'https://www.mattobell.net/',
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "views/account_move_view.xml",
        "report/account_invoice_report.xml",
        "report/invoice_report.xml"
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
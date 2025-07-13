{
    "name": "Currency Amount Words",
    "version": "1.6",
    "summary": "Currency Amount Words",
    "description": """
        This module overrides the amount in words to use dynamic currency names (e.g., Naira/Kobo, Dollar/Cents, etc.) in account.move.
    """,
    "depends": ["account"],
    'author': 'MOB - Ifeanyi Nneji',
    'website': 'https://www.mattobell.net/',
    "category": "Accounting",
    "data": [
        "views/account_move_views.xml",
        "report/report_invoice_document.xml",
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
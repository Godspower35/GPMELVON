{
    'name': 'MD Approval',
    'version': '0.0.7',
    'summary': 'Adds MD approval state to Sales, Purchase and Expenses',
    'description': """
        This module adds MD approval state to:
        - Sales Orders: before 'Quotation Sent'
        - Purchase Orders: after 'RFQ Sent'
        - Expense Sheets: after 'Approved by Manager'
    """,
    'category': 'Extra Tools',
    'author': 'MOB - Ifeanyi Nneji',
    'website': 'https://www.mattobell.net/',
    'depends': ['sale_management', 'purchase', 'hr_expense'],
    'data': [
        'data/mail_template_data.xml',
        'views/res_users_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/hr_expense_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
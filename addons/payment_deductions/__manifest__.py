{
    "name": "Payment Deductions",
    "version": "0.2.5", 
    "author": "MOB - Ifeanyi Nneji",
    "website": "https://www.mattobellonline.com",
    "category": "Accounting",
    "summary": "Add automatic deductions to payment journal entries based on account settings.",
    "description": """
This module enhances the Odoo payment process by introducing automatic deduction fields to payment journal entries.

The following deductions are supported:
- Discounts
- Administrative fees 
- Stamp duty
- Withholding tax (incoming)
- Withholding tax (outgoing)
- Withholding tax (outgoing 3%)
- Advertising fees

The deduction accounts can be configured through a wizard accessible from the payment form view or from the Accounting Configuration menu. Once configured, these deductions are applied automatically when the payment is confirmed.
    """,
    "depends": [
        "account",
        "account_accountant",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_payment_wizard.xml",
        "views/account_payment_views.xml", 
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}

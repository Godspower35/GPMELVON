from odoo import models, fields

class BankRecWidgetLine(models.AbstractModel):
    _inherit = "bank.rec.widget.line"

    account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_account_id',
        store=True,
        readonly=False,
        check_company=True,
        domain="[('deprecated', '=', False), ('id', '!=', journal_default_account_id)]",
    ) 
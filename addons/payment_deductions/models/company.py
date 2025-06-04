from odoo import models, fields, api


class CompanyInherit(models.Model):
    _inherit = 'res.company'

    stamp_account = fields.Many2one('account.account',
                                    string='Stamp Account', readonly=False)
    withholding_in_account = fields.Many2one('account.account', string='Withholding(IN)',
                                             readonly=False)
    withholding_out_account = fields.Many2one('account.account', string='Withholding(OUT)',
                                              readonly=False)
    withholding_out_account_3 = fields.Many2one('account.account', string='Withholding(OUT)',
                                              readonly=False)
    advertising_account = fields.Many2one('account.account', string='Advertising Account',
                                          readonly=False)
    discount_account = fields.Many2one('account.account', string='Discount Account',
                                       readonly=False)
    admin_fees = fields.Many2one('account.account', string='Admin Fees',
                                       readonly=False)

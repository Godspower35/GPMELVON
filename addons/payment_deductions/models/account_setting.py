from odoo import api, fields, models, _


class AccountSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    stamp_account = fields.Many2one('account.account',
                                    string='Stamp Account', related='company_id.stamp_account', readonly=False)
    withholding_in_account = fields.Many2one('account.account', string='Withholding(IN)', related='company_id.withholding_in_account',
                                    readonly=False)
    withholding_out_account = fields.Many2one('account.account', string='Withholding(OUT)',related='company_id.withholding_out_account',
                                              readonly=False)
    withholding_out_account_3 = fields.Many2one('account.account', string='Withholding(OUT-3)',related='company_id.withholding_out_account_3',
                                              readonly=False)
    advertising_account = fields.Many2one('account.account', related='company_id.advertising_account', string='Advertising Account',
                                          readonly=False)
    discount_account = fields.Many2one('account.account', related='company_id.discount_account', string='Discount Account',
                                       readonly=False)
    admin_fees = fields.Many2one('account.account', string='Admin Fees',related='company_id.admin_fees',
                                 readonly=False)


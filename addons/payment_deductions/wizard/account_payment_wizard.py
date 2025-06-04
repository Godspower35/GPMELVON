from odoo import models, fields, api

class PaymentAccountsWizard(models.TransientModel):
    _name = 'payment.accounts.wizard'
    _description = 'Configure Payment Accounts'

    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    stamp_account_id = fields.Many2one('account.account', string='Stamp Account')
    withholding_in_account_id = fields.Many2one('account.account', string='Withholding (Incoming)')
    withholding_out_account_id = fields.Many2one('account.account', string='Withholding (Outgoing)')
    withholding_out_account_3_id = fields.Many2one('account.account', string='Withholding (Outgoing 3%)')
    advertising_account_id = fields.Many2one('account.account', string='Advertising Account')
    discount_account_id = fields.Many2one('account.account', string='Discount Account')
    admin_fees_account_id = fields.Many2one('account.account', string='Admin Fees Account')

    @api.model
    def default_get(self, fields_list):
        res = super(PaymentAccountsWizard, self).default_get(fields_list)
        company = self.env.company
        res.update({
            'stamp_account_id': company.stamp_account.id,
            'withholding_in_account_id': company.withholding_in_account.id,
            'withholding_out_account_id': company.withholding_out_account.id,
            'withholding_out_account_3_id': company.withholding_out_account_3.id,
            'advertising_account_id': company.advertising_account.id,
            'discount_account_id': company.discount_account.id,
            'admin_fees_account_id': company.admin_fees.id,
        })
        return res

    def save_accounts(self):
        self.ensure_one()
        company = self.company_id
        company.write({
            'stamp_account': self.stamp_account_id.id,
            'withholding_in_account': self.withholding_in_account_id.id,
            'withholding_out_account': self.withholding_out_account_id.id,
            'withholding_out_account_3': self.withholding_out_account_3_id.id,
            'advertising_account': self.advertising_account_id.id,
            'discount_account': self.discount_account_id.id,
            'admin_fees': self.admin_fees_account_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
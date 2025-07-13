from odoo import models, fields, api

class PaymentAccountsWizard(models.TransientModel):
    _name = 'payment.accounts.wizard'
    _description = 'Configure Payment Accounts'

    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    
    # Radio button for account type selection
    account_type = fields.Selection([
        ('inbound', 'Inbound Payment Accounts'),
        ('outbound', 'Outbound Payment Accounts')
    ], string='Account Type', default='inbound', required=True)
    
    # Inbound Payment Accounts
    wht_receivables_inbound_id = fields.Many2one('account.account', string='WHT Receivables')
    vat_receivables_inbound_id = fields.Many2one('account.account', string='VAT Receivables')
    wht_payables_inbound_id = fields.Many2one('account.account', string='WHT Payables')
    ncd_inbound_id = fields.Many2one('account.account', string='NCD')
    exchange_gain_loss_inbound_id = fields.Many2one('account.account', string='Exchange Gain/Loss')
    ncd_payables_inbound_id = fields.Many2one('account.account', string='NCD Payables')
    vat_payables_inbound_id = fields.Many2one('account.account', string='VAT Payables')

    # Outbound Payment Accounts
    wht_receivables_outbound_id = fields.Many2one('account.account', string='WHT Receivables')
    vat_receivables_outbound_id = fields.Many2one('account.account', string='VAT Receivables')
    wht_payables_outbound_id = fields.Many2one('account.account', string='WHT Payables')
    ncd_outbound_id = fields.Many2one('account.account', string='NCD')
    exchange_gain_loss_outbound_id = fields.Many2one('account.account', string='Exchange Gain/Loss')
    ncd_payables_outbound_id = fields.Many2one('account.account', string='NCD Payables')
    vat_payables_outbound_id = fields.Many2one('account.account', string='VAT Payables')

    @api.model
    def default_get(self, fields_list):
        res = super(PaymentAccountsWizard, self).default_get(fields_list)
        company = self.env.company
        res.update({
            'wht_receivables_inbound_id': company.wht_receivables_inbound.id,
            'vat_receivables_inbound_id': company.vat_receivables_inbound.id,
            'wht_payables_inbound_id': company.wht_payables_inbound.id,
            'ncd_inbound_id': company.ncd_inbound.id,
            'exchange_gain_loss_inbound_id': company.exchange_gain_loss_inbound.id,
            'ncd_payables_inbound_id': company.ncd_payables_inbound.id,
            'vat_payables_inbound_id': company.vat_payables_inbound.id,
            'wht_receivables_outbound_id': company.wht_receivables_outbound.id,
            'vat_receivables_outbound_id': company.vat_receivables_outbound.id,
            'wht_payables_outbound_id': company.wht_payables_outbound.id,
            'ncd_outbound_id': company.ncd_outbound.id,
            'exchange_gain_loss_outbound_id': company.exchange_gain_loss_outbound.id,
            'ncd_payables_outbound_id': company.ncd_payables_outbound.id,
            'vat_payables_outbound_id': company.vat_payables_outbound.id,
        })
        return res

    def save_accounts(self):
        self.ensure_one()
        company = self.company_id
        company.write({
            'wht_receivables_inbound': self.wht_receivables_inbound_id.id,
            'vat_receivables_inbound': self.vat_receivables_inbound_id.id,
            'wht_payables_inbound': self.wht_payables_inbound_id.id,
            'ncd_inbound': self.ncd_inbound_id.id,
            'exchange_gain_loss_inbound': self.exchange_gain_loss_inbound_id.id,
            'ncd_payables_inbound': self.ncd_payables_inbound_id.id,
            'vat_payables_inbound': self.vat_payables_inbound_id.id,
            'wht_receivables_outbound': self.wht_receivables_outbound_id.id,
            'vat_receivables_outbound': self.vat_receivables_outbound_id.id,
            'wht_payables_outbound': self.wht_payables_outbound_id.id,
            'ncd_outbound': self.ncd_outbound_id.id,
            'exchange_gain_loss_outbound': self.exchange_gain_loss_outbound_id.id,
            'ncd_payables_outbound': self.ncd_payables_outbound_id.id,
            'vat_payables_outbound': self.vat_payables_outbound_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
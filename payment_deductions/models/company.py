from odoo import models, fields, api


class CompanyInherit(models.Model):
    _inherit = 'res.company'

    # Inbound Payment Accounts
    wht_receivables_inbound = fields.Many2one('account.account', string='WHT Receivables (Inbound)', readonly=False)
    vat_receivables_inbound = fields.Many2one('account.account', string='VAT Receivables (Inbound)', readonly=False)
    wht_payables_inbound = fields.Many2one('account.account', string='WHT Payables (Inbound)', readonly=False)
    ncd_inbound = fields.Many2one('account.account', string='NCD (Inbound)', readonly=False)
    exchange_gain_loss_inbound = fields.Many2one('account.account', string='Exchange Gain/Loss (Inbound)', readonly=False)
    ncd_payables_inbound = fields.Many2one('account.account', string='NCD Payables (Inbound)', readonly=False)
    vat_payables_inbound = fields.Many2one('account.account', string='VAT Payables (Inbound)', readonly=False)

    # Outbound Payment Accounts
    wht_receivables_outbound = fields.Many2one('account.account', string='WHT Receivables (Outbound)', readonly=False)
    vat_receivables_outbound = fields.Many2one('account.account', string='VAT Receivables (Outbound)', readonly=False)
    wht_payables_outbound = fields.Many2one('account.account', string='WHT Payables (Outbound)', readonly=False)
    ncd_outbound = fields.Many2one('account.account', string='NCD (Outbound)', readonly=False)
    exchange_gain_loss_outbound = fields.Many2one('account.account', string='Exchange Gain/Loss (Outbound)', readonly=False)
    ncd_payables_outbound = fields.Many2one('account.account', string='NCD Payables (Outbound)', readonly=False)
    vat_payables_outbound = fields.Many2one('account.account', string='VAT Payables (Outbound)', readonly=False)

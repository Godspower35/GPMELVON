from odoo import models, fields, api

class PaymentNotificationRule(models.Model):
    _name = 'payment.notification.rule'
    _description = 'Payment Notification Rules'

    name = fields.Char('Name', required=True)
    action = fields.Selection([
        ('confirm', 'Confirmation'),
        ('internal_approve', 'Internal Control Approval'),
        ('md_approve', 'MD Approval'),
        ('pay', 'Payment'),
    ], string='Action', required=True)
    user_ids = fields.Many2many('res.users', string='Users to Notify')
    active = fields.Boolean(default=True)
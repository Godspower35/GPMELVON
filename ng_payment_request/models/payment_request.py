from odoo import models
from odoo.tools.translate import _

class PaymentRequest(models.Model):
    _inherit = 'payment.requisition'

    def _get_notification_users(self, action):
        rules = self.env['payment.notification.rule'].search([
            ('action', '=', action),
            ('active', '=', True)
        ])
        users = self.env['res.users']
        for rule in rules:
            users |= rule.user_ids
        return users

    def notify(self, body, subject, users=None, group=None):
        if group:  # Override group-based notification
            action_map = {
                'ng_payment_request.group_internal': 'confirm',
                'ng_payment_request.group_manager': 'internal_approve',
                'account.group_account_invoice': 'md_approve',
            }
            action = action_map.get(group)
            if action:
                users = self._get_notification_users(action)
        
        template = self.env.ref('ng_payment_request.payment_notification_email_template')
        if users:
            for user in users:
                template.with_context(
                    body=body,
                    subject=subject,
                ).send_mail(
                    self.id,
                    force_send=True,
                    email_values={'email_to': user.partner_id.email}
                )
        return True
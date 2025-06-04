from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime, date


class Account_checkInherit(models.Model):
    _inherit = 'account.check'

    def send_check_date_notification(self):
        today = date.today()
        one_day_from_today = today + timedelta(days=1)

        contracts_to_notify = self.search([('payment_date', '=', one_day_from_today)])
        assign_to_users = self.env.user
        # print('one_day_from_today',one_day_from_today)
        # print('contracts_to_notify',contracts_to_notify)
        # print('assign_to_users',assign_to_users)
        if assign_to_users:

            # hr_manager_group = self.env.ref('hr.group_hr_manager')
            # users_to_send_mail = hr_manager_group.mapped('users')

            for contract in contracts_to_notify:
                full_mail = (_('The Check Number  %s has one day  for the due date . Sent by %s') % (
                    contract.name, self.env.user.name))
                for user in assign_to_users:
                    mail_values = {
                        'auto_delete': True,
                        'author_id': self.env.user.partner_id.id,
                        'email_from': self.env.user.partner_id.email_formatted,
                        'email_to': user.email_formatted,
                        'body_html': full_mail,
                        'subject': full_mail,
                    }
                    mail = self.env['mail.mail'].sudo().create(mail_values)
                    mail.sudo().send()

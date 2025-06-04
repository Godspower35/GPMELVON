from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submit', 'Submitted'),
            ('approve', 'Approved'),
            ('md_approval', 'MD Approval'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('cancel', 'Refused')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )
    def action_md_approval(self):
        self.write({'state': 'md_approval'})
        template = self.env.ref('mob_md_approval.mail_template_expense_md_approval')
        md_users = self.env['res.users'].search([('is_md', '=', True)])
        if not md_users:
            raise UserError(_("No Managing Directors defined. Please configure at least one user as MD."))
        for user in md_users:
            template.send_mail(self.id, force_send=True, email_values={'recipient_ids': [(6, 0, [user.partner_id.id])]})
        return True
    
    def action_md_approve(self):
        if not self.env.user.is_md:
            raise AccessError(_("Only Managing Directors can approve this document."))
        return self.action_sheet_move_post()
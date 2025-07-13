from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('md_approval', 'MD Approval'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    
    is_locked = fields.Boolean(compute='_compute_is_locked', store=False)
        
    sale_order_count = fields.Integer(
        string="Sale Orders",
        store=True,
        default=0
    )
    
    @api.depends('state')
    def _compute_is_locked(self):
        for record in self:
            record.is_locked = record.state in ['purchase', 'done']
    
    def action_md_approval(self):
        self.write({'state': 'md_approval'})
        template = self.env.ref('mob_md_approval.mail_template_purchase_md_approval')
        md_users = self.env['res.users'].search([('is_md', '=', True)])
        if not md_users:
            raise UserError(_("No Managing Directors defined. Please configure at least one user as MD."))
        for user in md_users:
            template.send_mail(self.id, force_send=True, email_values={'recipient_ids': [(6, 0, [user.partner_id.id])]})
        return True

    def print_quotation(self):
        self.action_md_approval()
        return self.env.ref('purchase.report_purchase_quotation').report_action(self)    
      
    def action_md_approve(self):
        if not self.env.user.is_md:
            raise AccessError(_("Only Managing Directors can approve this document"))

        _logger.info('MD approving purchase order: %s', self.mapped('name'))

        self.with_context(bypass_lock=True).write({'state': 'purchase'})
        for order in self:
            _logger.info(f"Calling _create_picking for {order.name} with bypass_lock context")
            order.with_context(bypass_lock=True)._create_picking()
        return True

    
    
    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'email_notification_allow_footer': True,
            'force_email': True,
            'mark_rfq_as_sent': self.state == 'draft',
        })

        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        if self.state == 'draft':
            self.write({'state': 'sent'})
            self.action_md_approval()

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
    def write(self, vals):
        for record in self:
            is_modification_allowed = False

            if self.env.context.get('bypass_lock'):
                is_modification_allowed = True
            else:
                if record.state == 'md_approval' and vals.get('state') == 'purchase':
                    is_modification_allowed = True
                else:
                    if record.state not in ['purchase', 'done']:
                        is_modification_allowed = True
                    else:
                        allowed_state_change = False
                        if 'state' in vals:
                            if vals.get('state') == record.state:
                                allowed_state_change = True

                        if not allowed_state_change:
                             is_modification_allowed = False
                        else:
                             is_modification_allowed = True

            if not is_modification_allowed:
                raise UserError(_("Cannot modify a locked Purchase Order (State: %s).") % record.state)

        return super(PurchaseOrder, self).write(vals)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        for line in self:
            if line.order_id.is_locked:
                raise UserError(_("Cannot modify product lines of a locked Purchase Order."))
        return super(PurchaseOrderLine, self).write(vals)

    def unlink(self):
        for line in self:
            if line.order_id.is_locked:
                raise UserError(_("Cannot delete product lines of a locked Purchase Order."))
        return super(PurchaseOrderLine, self).unlink()
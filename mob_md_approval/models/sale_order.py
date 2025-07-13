from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)

SALE_ORDER_STATE = [
    ('draft', "Quotation"),
    ('md_approval', "MD Approval"),
    ('sent', "Quotation Sent"),
    ('sale', "Sales Order"),
    ('cancel', "Cancelled"),
]

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    state = fields.Selection(
        selection=SALE_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    
    is_locked = fields.Boolean(compute='_compute_is_locked', store=False)
    
    @api.depends('state')
    def _compute_is_locked(self):
        for record in self:
            record.is_locked = record.state == 'sale'
    
    def action_md_approval(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft quotations can be submitted for MD approval."))
        self.write({'state': 'md_approval'})
        template = self.env.ref('mob_md_approval.mail_template_sale_md_approval')
        md_users = self.env['res.users'].search([('is_md', '=', True)])
        if not md_users:
            raise UserError(_("No Managing Directors defined. Please configure at least one user as MD."))
        for user in md_users:
            template.send_mail(self.id, force_send=True, email_values={'recipient_ids': [(6, 0, [user.partner_id.id])]})
        _logger.info(f"Sale Order {self.name} submitted for MD approval.")
        return True
    
    def action_md_approve(self):
        self.ensure_one()
        if not self.env.user.is_md:
            raise AccessError(_("Only Managing Directors can approve this document."))
        if self.state != 'md_approval':
            raise UserError(_("Only orders in 'MD Approval' state can be approved."))
        return self.action_quotation_send()
    
    purchase_order_count = fields.Integer(
        string="Purchase Orders",
        store=True,
        default=0
    )
    
    def action_quotation_send(self):
        self.ensure_one()
        # Allow state transition in all states except 'cancel'
        if self.state == 'cancel':
            raise UserError(_("Cannot process a cancelled quotation."))
        
        # Only update state to 'sent' if in 'draft' or 'md_approval'
        if self.state in ['draft', 'md_approval']:
            self.write({'state': 'sent'})
            _logger.info(f"Sale Order {self.name} moved to 'sent' state.")
        
        # Call the parent method to retain default behavior
        return super(SaleOrder, self).action_quotation_send()
    
    def action_confirm(self):
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_("Sale Order must be in 'Quotation Sent' state to confirm."))
        _logger.info(f"Confirming Sale Order {self.name} from 'sent' to 'sale'. Current is_locked: {self.is_locked}")
        self = self.with_context(bypass_lock=True)
        res = super(SaleOrder, self).action_confirm()
        _logger.info(f"Sale Order {self.name} confirmed successfully. New state: {self.state}")
        return res

    def write(self, vals):
        for record in self:
            if self.env.context.get('bypass_lock'):
                _logger.debug(f"Bypassing lock for {record.name} during write.")
                continue
            if record.state == 'sale' and record.is_locked:
                if 'state' in vals and vals.get('state') == 'sale' and record.state != 'sale':
                    _logger.debug(f"Allowing transition to 'sale' for {record.name}")
                    continue
                raise UserError(_("Cannot modify a locked Sales Order in 'sale' state."))
        return super(SaleOrder, self).write(vals)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, vals):
        for line in self:
            if line.order_id.state == 'sale' and line.order_id.is_locked and not self.env.context.get('bypass_lock'):
                raise UserError(_("Cannot modify product lines of a locked Sales Order."))
        return super(SaleOrderLine, self).write(vals)

    def unlink(self):
        for line in self:
            if line.order_id.state == 'sale' and line.order_id.is_locked and not self.env.context.get('bypass_lock'):
                raise UserError(_("Cannot delete product lines of a locked Sales Order."))
        return super(SaleOrderLine, self).unlink()
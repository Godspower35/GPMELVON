# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InvoiceAdd(models.Model):
    _name = "invoice.addition"
    _description = "Invoice Prepayment of addition"

    product_id = fields.Many2one('product.product', string='Product', required=False)
    journal_id = fields.Many2one('account.journal', string='Destination Journal', required=True, domain="[('type','=','purchase')]")

    # Remove # Remove api.multi
    def open_invoice(self):
        invoice_ids = []
        res = self.create_invoice()
        invoice_ids = [res]
        inv_type = 'in_invoice'
        action_model = False
        action = {}
        if not invoice_ids:
            raise UserError(_('No Invoices were created'))
        if inv_type == "out_invoice":
            action_model, action_id = self.env.ref('account.action_invoice_list1')
        elif inv_type == "in_invoice":
            action_model, action_id = self.env.ref('account.action_invoice_list2')
        elif inv_type == "out_refund":
            action_model, action_id = self.env.ref('account.action_invoice_list3')
        elif inv_type == "in_refund":
            action_model, action_id = self.env.ref('account.action_invoice_list4')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.read(action_id)
            action['domain'] = "[('id','in', [" + ','.join(map(str, invoice_ids)) + "])]"
        return action
    
    # Remove # Remove api.multi
    def _prepare_invoice(self, browse_add, partner, inv_type, journal_id):
        account_id = partner.property_account_payable_id.id
        invoice_vals = {
            'name': browse_add.name,
            'origin': browse_add.name,
            'move_type': 'in_invoice',  # Updated from 'type' to 'move_type'
            'account_id': account_id,
            'partner_id': partner.id,
            'invoice_partner_display_name': partner.name,  # Updated from address_invoice_id
            'partner_shipping_id': partner.id,  # Updated from address_contact_id
            'narration': '',  # Updated from 'comment'
            'invoice_payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,  # Updated field name
            'fiscal_position_id': partner.property_account_position_id.id,  # Updated field name
            'invoice_date': browse_add.add_date,  # Updated from date_invoice
            'company_id': browse_add.company_id.id,
            'user_id': self.env.user.id,  # Updated from self._uid
        }
        if journal_id:
            invoice_vals['journal_id'] = int(journal_id)
        return invoice_vals
    
    @api.model  # Keep this as model method
    def _get_taxes_invoice(self, p):
        if p.taxes_id:
            return [x.id for x in p.taxes_id]
        return []
    
    @api.model  # Keep this as model method
    def _prepare_invoice_line(self, browse_add, p=False, inv_id=False, inv=False):
        name = browse_add.name
        origin = browse_add.name or ''

        if not browse_add.category_id.account_prepayment_id:
            raise UserError(_('Please specify Prepayment Account.'))

        return {
            'name': name,
            'origin': origin,
            'move_id': inv_id,  # Updated from invoice_id to move_id
            'account_id': browse_add.category_id.account_prepayment_id.id,
            'price_unit': browse_add.cost,
            'quantity': 1,
        }
    
    def create_invoice(self):
        model = self._context.get('active_model')
        if not model or model != 'account.prepayment':
            return {}
            
        model_pool = self.env[model]
        res_ids = self._context and self._context.get('active_ids', [])
        browse_add = model_pool.browse(res_ids)
        
        if browse_add[0].method_prepayment == 'new':
            raise UserError(_("Can not create invoice with given Method"))
        if not browse_add[0].state == 'approve':
            raise UserError(_("Can not create invoice if prepayment addition not approved."))
        if browse_add[0].invoice_id:
            raise UserError(_("Invoice already create for the addition"))
        if not browse_add[0].partner_id:
            raise UserError(_("Please select partner."))

        data = self.read()[0]
        partner = browse_add[0].partner_id
        inv = self._prepare_invoice(browse_add[0], partner, 'in_invoice', data['journal_id'][0])
        inv_id = self.env['account.move'].create(inv)  # Updated from account.move to account.move
        p = False
        line = self._prepare_invoice_line(browse_add[0], p, inv_id.id, inv)
        inv_id_line = self.env['account.move.line'].create(line)  # Updated from account.move.line to account.move.line
        action_model, action_id = self.env.ref('account.action_move_in_invoice_type')  # Updated reference
        browse_add[0].write({'invoice_id': inv_id.id})
        return inv_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
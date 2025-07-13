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

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

class account_invoice(models.Model):
    _inherit = 'account.move'
    
    # Remove api.multi
    def action_number(self):
        result = super(account_invoice, self).action_number()
        for inv in self:
            self.env['account.move.line'].prepayment_create(inv.line_ids)
        return result
    
    @api.model
    def line_get_convert(self, x, part):
        res = super(account_invoice, self).line_get_convert(x, part)
        res['prepayment_id'] = x.get('prepayment_id', False)
        return res

    @api.model
    def create(self, vals):
        record = super(account_invoice, self).create(vals)
        self.env['account.move.line'].prepayment_create(record.line_ids)
        return record

    def write(self, vals):
        result = super(account_invoice, self).write(vals)
        if 'line_ids' in vals or 'invoice_line_ids' in vals:
            self.env['account.move.line'].prepayment_create(self.line_ids)
        return result

class account_invoice_line(models.Model):
    _inherit = 'account.move.line'
    
    prepayment_category_id = fields.Many2one('account.prepayment.category', string='Prepayment Category')
    
    # Remove api.multi
    def onchange_pcat(self, category_id):
        res = {'value':{}}
        pre_cat = self.env['account.prepayment.category']
        if category_id:
            category_obj = pre_cat.browse(category_id)
            res['value'] = {
                'account_id': category_obj.account_prepayment_id and category_obj.account_prepayment_id.id or False,
            }
        return res
    
    @api.model
    def prepayment_create(self, lines):
        prepayment_obj = self.env['account.prepayment']
        for line in lines:
            # Add debug logging
            _logger.info(f"Processing line: {line.name}, has category: {bool(line.prepayment_category_id)}")
            if line.prepayment_category_id:
                vals = {
                    'name': line.name,
                    'code': line.move_id.ref or '',
                    'category_id': line.prepayment_category_id.id,
                    'purchase_value': line.price_subtotal,
                    'original_amount': line.price_subtotal,
                    'partner_id': line.move_id.partner_id.id,
                    'company_id': line.move_id.company_id.id,
                    'currency_id': line.move_id.currency_id.id,
                    'purchase_date': line.move_id.invoice_date
                }
                changed_vals = prepayment_obj.onchange_category_id(vals['category_id'])
                vals.update(changed_vals['value'])
                prepayment_id = prepayment_obj.create(vals)
                if line.prepayment_category_id.open_prepayment:
                    prepayment_id.validate()
        return True

class purchase(models.Model):
    _inherit = 'purchase.order'
    
    # Remove api.multi
    def wkf_confirm_order(self):
        result = super(purchase, self).wkf_confirm_order()
        for inv in self:
            pass
#            self.pool.get('purchase.order.line').prepayment_create(cr, uid, inv.order_line)
        return result
    
    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        """Collects require data from purchase order line that is used to create invoice line 
        for that purchase order line
        :param account_id: Expense account of the product of PO line if any.
        :param browse_record order_line: Purchase order line browse record
        :return: Value for fields of invoice lines.
        :rtype: dict
        """
        return {
            'name': order_line.name,
            'account_id': account_id,
            'price_unit': order_line.price_unit or 0.0,
            'quantity': order_line.product_qty,
            'product_id': order_line.product_id.id or False,
            'uos_id': order_line.product_uom.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in order_line.taxes_id])],
            'account_analytic_id': order_line.account_analytic_id.id or False,
            'prepayment_category_id': order_line.pre_category_id.id
        }

class po_line(models.Model):
    _inherit = 'purchase.order.line'

    pre_category_id = fields.Many2one('account.prepayment.category', string='Prepayment Category')
    
    # @api.depends('default')
    def copy_data(self, default=None):
        if not default:
            default = {}
        default.update({'pre_category_id':False})
        return super(po_line, self).copy_data(default)
    
    @api.model
    def prepayment_create(self, lines):
        pre_obj = self.env['account.prepayment']
        for line in lines:
            if line.pre_category_id:
                vals = {
                    'name': line.name,
                    'code': line.order_id.name or False,
                    'category_id': line.pre_category_id.id,
                    'purchase_value': line.price_subtotal,
                    'original_amount': line.price_subtotal,
                    'partner_id': line.order_id.partner_id.id,
                    'company_id': line.order_id.company_id.id,
                    'currency_id': line.order_id.company_id.currency_id.id,
                }
                changed_vals = pre_obj.onchange_category_id(vals['category_id'])
                vals.update(changed_vals['value'])
                pre_id = pre_obj.create(vals)
                if line.pre_category_id.open_prepayment:
                    pre_id.validate()
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

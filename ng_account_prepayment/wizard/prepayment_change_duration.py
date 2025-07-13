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
import time
from lxml import etree

from odoo import models, fields, api, _

class PrepaymentModify(models.Model):
    _name = 'prepayment.modify'
    _description = 'Modify Prepayment'

    name = fields.Char(string='Reason', required=True)
    method_number = fields.Integer(string='Number of Depreciations', required=True)
    method_period = fields.Integer(string='Period Length')
    method_end = fields.Date(string='Ending date')
    note = fields.Text(string='Notes')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Returns views and fields for current model.
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param view_id: list of fields, which required to read signatures
        @param view_type: defines a view type. it can be one of (form, tree, graph, calender, gantt, search, mdx)
        @param context: context arguments, like lang, time zone
        @param toolbar: contains a list of reports, wizards, and links related to current model

        @return: Returns a dictionary that contains definition for fields, views, and toolbars
        """
        prepayment_obj = self.env['account.prepayment']
        result = super(PrepaymentModify, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        prepayment_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', '')
        if active_model == 'account.prepayment' and prepayment_id:
            prepayment = prepayment_obj.browse(prepayment_id)
            doc = etree.XML(result['arch'])
            if prepayment.method_time == 'number':
                node = doc.xpath("//field[@name='method_end']")[0]
                node.set('invisible', '1')
            elif prepayment.method_time == 'end':
                node = doc.xpath("//field[@name='method_number']")[0]
                node.set('invisible', '1')
            result['arch'] = etree.tostring(doc)
        return result
    
    @api.model
    def default_get(self, fields):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values 
        @param context: A standard dictionary 
        @return: A dictionary which of fields with values. 
        """ 
        prepayment_obj = self.env['account.prepayment']
        res = super(PrepaymentModify, self).default_get(fields)
        prepayment_id = self._context.get('active_id', False)
        prepayment = prepayment_obj.browse(prepayment_id)
        if 'name' in fields:
            res.update({'name': prepayment.name})
        if 'method_number' in fields and prepayment.method_time == 'number':
            res.update({'method_number': prepayment.method_number})
        if 'method_period' in fields:
            res.update({'method_period': prepayment.method_period})
        if 'method_end' in fields and prepayment.method_time == 'end':
            res.update({'method_end': prepayment.method_end})
        return res
    
    def modify(self):
        """ Modifies the duration of prepayment for calculating depreciation
        and maintains the history of old values.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of Ids 
        @param context: A standard dictionary 
        @return: Close the wizard. 
        """ 
        prepayment_obj = self.env['account.prepayment']
        history_obj = self.env['account.prepayment.history']
        prepayment_id = self._context.get('active_id', False)
        if not prepayment_id:
            return {'type': 'ir.actions.act_window_close'} 
        prepayment = prepayment_obj.browse(prepayment_id)
        data = self
        history_vals = {
            'prepayment_id': prepayment_id,
            'name': data.name,
            'method_time': prepayment.method_time,
            'method_number': prepayment.method_number,
            'method_period': prepayment.method_period,
            'method_end': prepayment.method_end,
            'user_id': self._uid,
            'date': time.strftime('%Y-%m-%d'),
            'note': data.note,
        }
        history_obj.create(history_vals)
        prepayment_vals = {
            'method_number': data.method_number,
            'method_period': data.method_period,
            'method_end': data.method_end,
        }
        prepayment_id.write(prepayment_vals)
        prepayment_id.compute_depreciation_board()
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
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

from odoo import models, fields, api, _

class PrepaymentDepreciationConfirmationWizard(models.Model):
    _name = "perpayment.depreciation.confirmation.wizard"
    _description = "perpayment.depreciation.confirmation.wizard"
    
    date_start = fields.Date('Start Date', required=True)
    date_end = fields.Date('End Date', required=True)
    
    def perpayment_compute(self):
        ass_obj = self.env['account.prepayment']
        perpayment_ids = ass_obj.search([('state','=','open')])
        data = self.read(['date_start', 'date_end'])[0]
        created_move_ids = perpayment_ids._compute_entries(data['date_start'], data['date_end'])
        return {
            'name': _('Created Prepayment Moves'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',["+','.join(map(str,created_move_ids))+"])]",
            'type': 'ir.actions.act_window',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
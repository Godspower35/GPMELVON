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

{
    'name' : 'Prepayment Management',
    'version' : '18.0.0.0',
    'depends' : ['account', 'purchase'],
    'author' : "Matt O'bell",
    'website' : 'http://www.mattobell.net',
    'description': '''
    Modules to manage prepayment.
    ''',
    'category' : 'Accounting & Finance',
    'sequence': 32,
    'data' : [
        'security/ng_account_prepayment_security.xml',
        'security/ir.model.access.csv',
        'wizard/wizard_prepayment_compute_view.xml',
        'wizard/prepayment_change_duration_view.xml',
        'wizard/invoice_create_view.xml',
        'views/ng_account_prepayment_view.xml',
        'views/prepayment_writeoff_view.xml',
        'views/ng_account_prepayment_invoice_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'icon': '/ng_account_prepayment/static/description/icon.png',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

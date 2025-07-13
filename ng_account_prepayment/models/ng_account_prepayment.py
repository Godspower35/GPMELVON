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

import logging
import time
from datetime import date, datetime
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class prepayment_category(models.Model):
    _name = 'account.prepayment.category'
    _description = 'Prepayment category'

    name = fields.Char(string='Name', required=True, select=1)
    note = fields.Text(string='Note')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    account_prepayment_id = fields.Many2one('account.account', string='Prepayment Account', required=True)

    account_expense_depreciation_id = fields.Many2one('account.account', string='Prepaid Expense Account', required=True) 
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.prepayment.category'))
    method_number = fields.Integer(string='Number of Prepayments', default=5)
    method_period = fields.Integer(string='Period Length', default=12, help="State here the time between 2 prepayemnts, in months to amortize", required=True)
    method_time = fields.Selection(selection=[('number', 'Number of Amortizations'), ('end', 'Ending Date')], default='number', string='Time Method', required=True,
                              help="Choose the method to use to compute the Dates and number of Prepayments lines.\n"\
                                   "  * Number of Prepayments: Fix the number of Prepayments lines and the time between 2 Prepayments.\n" \
                                   "  * Ending Date: Choose the time between 2 Prepayments and the Date the Prepayments won't go beyond.")
    method_end = fields.Date(string='Ending Date')
    open_prepayment = fields.Boolean(string='Skip Draft State', help="Check this if you want to automatically confirm the prepayments of this category when created by invoices.")


class prepayment(models.Model):
    _name = 'account.prepayment'
    _description = 'Prepayment'
    _inherit = ['mail.thread']
    
    # @api.depends('default')
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'depreciation_line_ids': [], 'state': 'draft'})
        return super(prepayment, self).copy(default)

    def action_view_amortization(self):
        self.ensure_one()
        return {
            'name': 'Amortization Board',
            'type': 'ir.actions.act_window',
            'res_model': 'account.prepayment.depreciation.line',
            'view_mode': 'list,graph',
            'domain': [('prepayment_id', '=', self.id)],
            'context': {'default_prepayment_id': self.id},
            'target': 'current'
        }
    
    # Remove api.multi
    def _get_last_depreciation_date(self):
        """
        """
        self._cr.execute("""
            SELECT a.id as id, COALESCE(MAX(l.date),a.purchase_date) AS date
            FROM account_prepayment a
            LEFT JOIN account_move_line l ON (l.prepayment_id = a.id)
            WHERE a.id IN %s
            GROUP BY a.id, a.purchase_date """, (tuple(self.ids),))
        return dict(self._cr.fetchall())
    

    def _compute_board_amount(self, prepayment, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
            if prepayment.prorata:
                date_start = fields.Date.from_string(prepayment.purchase_date)
                date_end_first_period = date_start + relativedelta(months=prepayment.method_period)
                days_in_first_period = (date_end_first_period - date_start).days

                if i == 1:
                    days_remaining = (date_end_first_period - depreciation_date).days
                    amount = (amount_to_depr / undone_dotation_number) * (days_remaining / days_in_first_period)
                else:
                    amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))

        return amount

    def _compute_board_undone_dotation_nb(self, prepayment, depreciation_date, total_days):
        undone_dotation_number = prepayment.method_number
        if prepayment.method_time == 'end':
            end_date = fields.Date.from_string(prepayment.method_end)
            undone_dotation_number = 0
            current_date = depreciation_date
            while current_date <= end_date:
                current_date += relativedelta(months=+prepayment.method_period)
                undone_dotation_number += 1
        if prepayment.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def compute_depreciation_board(self):
        _logger.info("compute_depreciation_board called!")
        depreciation_lin_obj = self.env['account.prepayment.depreciation.line']
        for prepayment in self:
            _logger.info(f"Processing prepayment: {prepayment.name}, ID: {prepayment.id}")

            if not prepayment.id:
                raise UserError("Prepayment ID is None!")

            posted_depreciation_line_ids = depreciation_lin_obj.search([
                ('prepayment_id', '=', prepayment.id),
                ('move_check', '=', True)
            ])
            _logger.info(f"  Posted depreciation lines: {posted_depreciation_line_ids}")

            old_depreciation_line_ids = depreciation_lin_obj.search([
                ('prepayment_id', '=', prepayment.id),
                ('move_id', '=', False)
            ])
            _logger.info(f"  Old depreciation lines to unlink: {old_depreciation_line_ids}")
            old_depreciation_line_ids.unlink()

            amount_to_depr = residual_amount = prepayment.original_amount  # Use original_amount

            _logger.info(f"Prepayment values: Residual Amount- {residual_amount}, Original Amount: {prepayment.original_amount}")

            # Correctly reduce residual_amount for posted lines *before* the loop.
            for line in posted_depreciation_line_ids:
                residual_amount -= line.amount

            purchase_date = fields.Date.from_string(prepayment.purchase_date)
            depreciation_date = purchase_date

            # Advance the depreciation_date by the correct number of periods
            for _ in range(len(posted_depreciation_line_ids)):
                depreciation_date += relativedelta(months=+prepayment.method_period)

            _logger.info(f"  Initial depreciation date: {depreciation_date}")

            total_days = 365  # Leap year calculation not needed in main loop

            undone_dotation_number = self._compute_board_undone_dotation_nb(prepayment, depreciation_date, total_days)
            if prepayment.prorata:
                undone_dotation_number -= 1  # Correctly handle prorata.

            _logger.info(f"  Undone dotation number: {undone_dotation_number}")

            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                i = x + 1
                amount = self._compute_board_amount(prepayment, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)
                residual_amount -= amount
                _logger.info(f"    Iteration {i}: amount={amount}, residual_amount={residual_amount}")

                if amount < 0.0:
                    _logger.info("Amount is negative after _compute_board_amount.  Adjusting.")
                    amount = 0.0  # Prevent negative depreciation

                vals = {
                    'amount': amount,
                    'prepayment_id': prepayment.id,
                    'sequence': i,
                    'name': str(prepayment.id) + '/' + str(i),
                    'remaining_value': residual_amount,
                    'depreciated_value': prepayment.original_amount - residual_amount,  # Simpler calculation
                    'depreciation_date': fields.Date.to_string(depreciation_date),
                }
                _logger.info(f"      Creating depreciation line with vals: {vals}")
                depreciation_lin_obj.create(vals)

                depreciation_date += relativedelta(months=+prepayment.method_period)

        return True

    def validate(self):
        move_obj = self.env['account.move']
        for a in self:
            if a.book_gl:
                move_vals = {
                    'date': fields.Date.today(),
                    'ref': a.name,
                    'journal_id': a.category_id.journal_id.id,
                }
                move_id = move_obj.create(move_vals)
                journal_id = a.category_id.journal_id.id
                partner_id = a.partner_id.id
                company_currency = a.company_id.currency_id
                current_currency = a.currency_id
                amount = current_currency._convert(a.purchase_value, company_currency, a.company_id, fields.Date.today())
                sign = 1 if a.category_id.journal_id.type == 'purchase' else -1

                vals11 = [(0, 0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id.id,
                    'account_id': a.gl_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': current_currency.id if company_currency.id != current_currency.id else False,
                    'amount_currency': -sign * a.purchase_value if company_currency.id != current_currency.id else 0.0,
                    'date': fields.Date.today(),
                }), (0, 0, {
                    'name': a.name,
                    'ref': a.name,
                    'move_id': move_id.id,
                    'account_id': a.category_id.account_prepayment_id.id,
                    'credit': 0.0,
                    'debit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': current_currency.id if company_currency.id != current_currency.id else False,
                    'amount_currency': sign * a.purchase_value if company_currency.id != current_currency.id else 0.0,
                    'date': fields.Date.today(),
                })]
                move_id.write({'line_ids': vals11})
                a.write({'move_id1': move_id.id})
        return self.write({'state': 'open'})

    def set_to_close(self):
        return self.write({'state': 'close'})

    @api.depends('depreciation_line_ids.move_check', 'depreciation_line_ids.amount', 'original_amount')
    def _amount_residual(self):
        for rec in self:
            total_depreciated = sum(line.amount for line in rec.depreciation_line_ids if line.move_check)
            rec.value_residual = rec.original_amount - total_depreciated

    @api.depends('depreciation_line_ids.move_check', 'depreciation_line_ids.amount')
    def _total_am(self):
        for rec in self:
            rec.total_am = sum(line.amount for line in rec.depreciation_line_ids if line.move_check)

    
    def set_to_close(self):
        return self.write({'state': 'close'})
    
    def onchange_company_id(self, company_id=False):
        val = {}
        if company_id:
            company = self.env['res.company'].browse(company_id)
            #if company.currency_id.company_id and company.currency_id.company_id.id != company_id:
            if False:#probusetodo
                val['currency_id'] = False
            else:
                val['currency_id'] = company.currency_id.id
        return {'value': val}

    value_residual = fields.Float(compute='_amount_residual', method=True, digits_compute=dp.get_precision('Account'), string='Closing Balance', store=True)
    total_am = fields.Float(compute='_total_am', method=True, digits_compute=dp.get_precision('Account'), string='Total Amortized', store=True)
    name = fields.Char(string='Name', required=True, states={'draft':[('readonly', False)]})
    method_prepayment = fields.Selection(selection=[('add', 'Additions to existing prepayment'), ('new', 'Transfer an existing prepayment')], string='Method', required=True, states={'draft':[('readonly', False)]},
                                            default='new',
                                            help="Choose the method to use for booking prepayments.\n" \
            " * Additions to existing prepayment: Add items to existing prepayment. \n"\
            " * Transfer an existing prepayment: select for an already existing prepayment. Journals must be raised in GL to book the transfer.\n Note: For new Purchases, Please use Supplier Purchases")
    cost = fields.Float(string='Additions', digits_compute=dp.get_precision('Account'), help='Amount of new prepaid items added.', required=False, states={'draft':[('readonly', False)]})
    user_id = fields.Many2one('res.users', string='Responsible User', states={'draft':[('readonly', False)]},
                              default=lambda self: self.env.user)
    add_date = fields.Date(string='Addition Date', required=False, states={'draft':[('readonly', False)]}, default=time.strftime('%Y-%m-%d'))
    recompute_prepayment = fields.Boolean(string='Extend Tenor', help='If checked, the additions will be used to recompute a new amortization schedule and spread over the period specified by the current prepaid item. if unchecked, the additions will be used to recompute a new amortization schedule over the period specified by the new addition.')
    add_notes = fields.Text(string='Addition Description', states={'draft':[('readonly', False)]})
    prepayment_id = fields.Many2one('account.prepayment', string='Prepayment', domain=[('method_prepayment', '=', 'new')], required=False, states={'draft':[('readonly', False)]})
    prepayment_gross = fields.Float(related='prepayment_id.value_residual', string='Closing Balance', store=True,)
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Running'), ('close', 'Closed'), ('open1', 'Confirmed'), ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], string='State', required=True,
                              help="When an prepayment or Additions is created, the state is 'Draft'.\n" \
                                   "If the prepayment is confirmed, the state goes in 'Running' and the Amortization lines can be posted in the accounting.\n" \
                                   "If the Additions is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the Additions is approved, the state goes in 'Approved' \n" \
                                   "If the Additions is rejected, the state goes in 'Rejected' \n" \
                                   "If the Additions is cancelled, the state goes in 'Cancelled' \n" \
                                   "You can manually close an prepayment when the Amortization is over. If the last line of Amortization is posted, the prepayment automatically goes in that state."
                                   , default='draft')
            
    add_history = fields.One2many('account.prepayment', 'prepayment_id', string='Addition History', states={'draft':[('readonly', False)]})
    
    allow_capitalize = fields.Boolean(string='Allow Capitalize', states={'draft':[('readonly', False)]}, default=False, help="Check this box if you want to allow capitalize cost of current prepayment.")
    book_gl = fields.Boolean(string='Book Transfer to GL?', states={'draft':[('readonly', False)]},)
    gl_account_id = fields.Many2one('account.account', string='GL Account', required=False, states={'draft':[('readonly', False)]})
    move_id1 = fields.Many2one('account.move', string='Journal Entry 1',)

    account_move_line_ids = fields.One2many('account.move.line', 'prepayment_id', string='Entries', states={'draft':[('readonly', False)]})
    name = fields.Char(string='Prepayment', required=True, states={'draft':[('readonly', False)]})
    code = fields.Char(string='Reference', states={'draft':[('readonly', False)]})
    purchase_value = fields.Float(string='Transferred Balance ', required=True, states={'draft':[('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, states={'draft':[('readonly', False)]}, default=lambda self:self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True, states={'draft':[('readonly', False)]}, default=lambda self:self.env['res.company']._company_default_get('account.prepayment'))
    note = fields.Text(string='Note')
    category_id = fields.Many2one('account.prepayment.category', string='Prepayment Category', required=True, change_default=True, states={'draft':[('readonly', False)]})
    parent_id = fields.Many2one('account.prepayment', string='Parent Prepayment', states={'draft':[('readonly', False)]}, domain=[('method_prepayment', '=', 'new')])
    child_ids = fields.One2many('account.prepayment', 'parent_id', string='Children Prepayments')
    purchase_date = fields.Date(string='Transfer Date', required=True, default=time.strftime('%Y-%m-%d'), states={'draft':[('readonly', False)]})
    active = fields.Boolean(string='Active', default=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=False, states={'draft':[('readonly', False)]})

    method_number = fields.Integer(string='Number of Amortizations', default=5, states={'draft':[('readonly', False)]}, help="Calculates Aamortization within specified interval")
    method_period = fields.Integer(string='Period Length', default=12, required=True, states={'draft':[('readonly', False)]}, help="State here the time during 2 Amortizations, in months to amortize")
    method_end = fields.Date(string='Ending Date', states={'draft':[('readonly', False)]})
    method_time = fields.Selection(selection=[('number', 'Number of Amortizations'), ('end', 'Ending Date')], string='Time Method', default='number', required=True, states={'draft':[('readonly', False)]},
                              help="Choose the method to use to compute the Dates and number of Amortization lines.\n"\
                                   "  * Number of Amortization: Fix the number of Amortization lines and the time between 2 Amortizations.\n" \
                                   "  * Ending Date: Choose the time between 2 Amortizations and the Date the Amortizations won't go beyond.")

    add_method_number = fields.Integer(string='Number of Amortizations for Addition', default=5, states={'draft':[('readonly', False)]}, help="Calculates Aamortization within specified interval")
    add_method_period = fields.Integer(string='Period Length for Addition', default=15, required=True, states={'draft':[('readonly', False)]}, help="State here the time during 2 Amortizations, in months to amortize")
    add_method_end = fields.Date(string='Ending Date for Addition', states={'draft':[('readonly', False)]})
    add_method_time = fields.Selection(selection=[('number', 'Number of Amortizations'), ('end', 'Ending Date')], string='Time Method for Addition', default='number', required=True, states={'draft':[('readonly', False)]},
                              help="Choose the method to use to compute the Dates and number of Amortization lines.\n"\
                                   "  * Number of Amortization: Fix the number of Amortization lines and the time between 2 Amortizations.\n" \
                                   "  * Ending Date: Choose the time between 2 Amortizations and the Date the Amortizations won't go beyond.")
    invoice_id = fields.Many2one('account.move', string='Invoice', help='Invoice reference for this prepayment.', copy=False)
    want_invoice = fields.Boolean(string='Invoice?', help='Tick if you want to create invoice from prepayment addition.', copy=False)
    prorata = fields.Boolean(string='Prorata Temporis', states={'draft':[('readonly', False)]}, help='Indicates that the first Amortization entry for this prepayment have to be done from the transfer date instead of the first January', default=True)
    history_ids = fields.One2many('account.prepayment.history', 'prepayment_id', string='History',)
    depreciation_line_ids = fields.One2many('account.prepayment.depreciation.line', 'prepayment_id', string='Amortization Lines', readonly=True, states={'draft':[('readonly', False)], 'open':[('readonly', False)]})
    original_amount = fields.Float(string='Original Amount', digits_compute=dp.get_precision('Account'), states={'draft':[('readonly', False)]})
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account', states={'draft':[('readonly', False)]},)
    
    # Remove api.multi
    def _check_recursion(self, parent=None):
        return super(prepayment, self)._check_recursion(parent=parent)
    
    # Remove api.multi
    @api.constrains('prorata')
    def _check_prorata(self):
        for pre in self:
            if pre.prorata and pre.method_time != 'number':
                raise UserError('Prorata temporis can be applied only for time method "number of depreciations".')
        return True
    
    # Remove api.multi
    def onchange_category_id(self, category_id):
        res = {'value':{}}
        pre_cat = self.env['account.prepayment.category']
        if category_id:
            category_obj = pre_cat.browse(category_id)
            res['value'] = {
                'method_number': category_obj.method_number,
                'method_time': category_obj.method_time,
                'method_period': category_obj.method_period,
                'method_end': category_obj.method_end,
                'account_analytic_id': category_obj.account_analytic_id.id,
            }
        return res
    
    # Remove api.multi
    def onchange_method_time(self, method_time='number'):
        res = {'value': {}}
        if method_time != 'number':
            res['value'] = {'prorata': False}
        return res
    
    # Remove api.multi
    def onchange_add_method_time(self, add_method_time='number'):
        res = {'value': {}}
        if add_method_time != 'number':
            res['value'] = {'prorata': False}
        return res
    
    @api.model
    def _compute_entries(self, date_start, date_stop):#pass date instead of period.... probusetodo ... calling from wizard....
        depreciation_obj = self.env['account.prepayment.depreciation.line']
        depreciation_ids = depreciation_obj.search([('prepayment_id', 'in', self.ids), ('depreciation_date', '<=', date_stop), ('depreciation_date', '>=', date_start), ('move_check', '=', False)])
        return depreciation_ids.create_move()
    
    def create(self, vals):
        _logger.info("jjjf")
        prepayment_id = super(prepayment, self).create(vals)
        prepayment_id.compute_depreciation_board()
        return prepayment_id

    # Remove api.multi
    def write(self, vals):
        res = super(prepayment, self).write(vals)
        if 'depreciation_line_ids' not in vals and 'state' not in vals:
            for rec in self:
                rec.compute_depreciation_board()
        return res

    # Remove api.multi
    def validate1(self):
        for cap in self:
            if cap.prepayment_id.state in ('draft', 'close'):
                raise UserError( _("You can not confirm Additions of prepayment when related prepayment is in Draft/Close state."))
        return self.write({'state': 'open'})
    
    # Remove api.multi
    def approve(self):
        for cap in self:
            if cap.prepayment_id.state in ('draft', 'close'):
                raise UserError( _("You can not approve Additions of prepayment when related prepayment is in Draft/Close state."))
            elif cap.method_prepayment == 'add':
                flag_amount = False
                cap.prepayment_id.write({'purchase_value': cap.prepayment_id.purchase_value + cap.cost})
                if cap.recompute_prepayment:
                    flag_amount = cap.cost + cap.prepayment_gross
                    vals = {
                        'method_number': cap.add_method_number,
                        'method_time': cap.add_method_time,
                        'method_period': cap.add_method_period,
                        'name': cap.name,
                        'method_end': cap.add_method_end
                    }
                    cap.prepayment_id.write(vals)
                else:
                    cap.prepayment_id.write({'name':cap.name})
                cap.prepayment_id.compute_depreciation_board(flag_amount=flag_amount)
        return self.write({'state': 'approve'})
    
    # Remove api.multi
    def set_to_draft_app(self):
        return self.write({'state': 'draft'})
    
    # Remove api.multi
    def set_to_draft(self):
        return self.write({'state': 'draft'})
    
    # Remove api.multi
    def set_to_close1(self):
        return self.write({'state': 'reject'})
    
    # Remove api.multi
    def set_to_cancel(self):
        return self.write({'state': 'cancel'})
    
    # Remove api.multi
    def onchange_prepayment(self, prepayment_id=False):
        res = {}
        res['value'] = {'category_id': False}
        if not prepayment_id:
            return res
        prepayment_obj = self.env['account.prepayment']
        
        if prepayment_id:
            close_bal = 0.0
            self._cr.execute("""SELECT
                    l.prepayment_id as id, round(SUM(abs(l.debit-l.credit))) AS amount
                FROM
                    account_move_line l
                WHERE
                    l.prepayment_id IN %s GROUP BY l.prepayment_id """, (tuple([prepayment_id]),))
            res1 = dict(self._cr.fetchall())
            for pre in self.browse(prepayment_id):
                close_bal = pre.purchase_value - res1.get(pre.id, 0.0)

            pre = prepayment_obj.browse(prepayment_id)
            res['value'].update({
#                            'name': pre.name,
            'category_id':pre.category_id.id,
            'add_method_number': pre.category_id.method_number,
            'add_method_time': pre.category_id.method_time,
            'add_method_period': pre.category_id.method_period,
            'add_method_end': pre.category_id.method_end,
            'value_residual': close_bal,
            })
        return res
    
    # Remove api.multi
    def onchange_cost(self, cost, prepayment_id=False):
        res = {}
        return res

class account_prepayment_depreciation_line(models.Model):
    _name = 'account.prepayment.depreciation.line'
    _description = 'Prepayment depreciation line'

    @api.depends('move_id')
    def _get_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    name = fields.Char(string='Amortization Name', required=True)
    sequence = fields.Integer(string='Sequence of the Amortization', required=True)
    prepayment_id = fields.Many2one('account.prepayment', string='Prepayment', required=True)
    parent_state = fields.Selection(related='prepayment_id.state', string='State of Prepayment')
    amount = fields.Float(string='Amortization Amount', required=True)
    remaining_value = fields.Float(string='Amount to Amortize', required=True)
    depreciated_value = fields.Float(string='Amount Already Amortized', required=True)
    depreciation_date = fields.Date(string='Amortization date', index=True)
    move_id = fields.Many2one('account.move', string='Amortization Entry')
    move_check = fields.Boolean(compute='_get_move_check', string='Posted', store=True)

    def last_day_of_month(self, year, month):
        """ Work out the last day of the month """
        _, last_day = monthrange(year, month)
        return date(year, month, last_day)

    def create_move(self):
        _logger.info("Starting create_move method")
        can_close = False
        created_move_ids = []
        for line in self:
            _logger.info(f"Processing line: {line.name}, sequence: {line.sequence}")

            if line.prepayment_id.currency_id.is_zero(line.remaining_value):
                _logger.info(f"Remaining value is zero, setting can_close to True. Remaining Value: {line.remaining_value}")
                can_close = True
            if line.depreciation_date > date.today():
                _logger.error("Depreciation date is in the future.")
                raise UserError(_("You are not allowed to create move beyond the current period."))

            depreciation_date = line.depreciation_date
            _logger.info(f"Initial depreciation date: {depreciation_date}")

            if line.remaining_value > 0.0:
                depreciation_date = self.last_day_of_month(depreciation_date.year, depreciation_date.month)
                _logger.info(f"Adjusted depreciation date to last day of month: {depreciation_date}")

            company_currency = line.prepayment_id.company_id.currency_id
            current_currency = line.prepayment_id.currency_id
            _logger.info(f"Company currency: {company_currency.name}, Prepayment currency: {current_currency.name}")

            # Make sure amount is not 0 before conversion
            if line.amount <= 0:
                _logger.error(f"Amortization Amount is zero or negative: {line.amount}")
                raise UserError(_("Cannot create a move with zero amount. Check the amortization calculation."))

            # Convert amount from prepayment currency to company currency
            amount = current_currency._convert(
                line.amount,
                company_currency,
                line.prepayment_id.company_id,
                depreciation_date
            )
            _logger.info(f"Amount before conversion: {line.amount} {current_currency.name}, after conversion: {amount} {company_currency.name}")

            # Make sure amount is positive for journal entries
            if amount <= 0:
                _logger.error(f"Converted amount is zero or negative: {amount}")
                raise UserError(_("Conversion resulted in zero or negative amount. Check currency rates."))
            
            pre_name = line.prepayment_id.name
            reference = line.name
            move_vals = {
                'date': depreciation_date,
                'ref': reference,
                'journal_id': line.prepayment_id.category_id.journal_id.id,
            }
            _logger.info(f"Creating move with values: {move_vals}")

            move_id = self.env['account.move'].create(move_vals) #removed with_context
            _logger.info(f"Created move_id: {move_id.id}")  # Log the ID of the created move

            journal_id = line.prepayment_id.category_id.journal_id.id
            partner_id = line.prepayment_id.partner_id.id

            # Determine the analytic account ID
            analytic_account_id = line.prepayment_id.account_analytic_id.id or line.prepayment_id.category_id.account_analytic_id.id or False
            _logger.info(f"Journal ID: {journal_id}, Partner ID: {partner_id}, Analytic Account ID: {analytic_account_id}")
            _logger.info(f'Creating move lines with amount: {amount}')


            # Create move lines
            vals11 = [
                (0, 0, {
                    'name': pre_name,
                    'ref': reference,
                    'move_id': move_id.id,
                    'account_id': line.prepayment_id.category_id.account_prepayment_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id if company_currency == current_currency else current_currency.id,
                    'amount_currency': -line.amount if company_currency != current_currency else 0.0,
                    'date': depreciation_date,
                }),
                (0, 0, {
                    'name': pre_name,
                    'ref': reference,
                    'move_id': move_id.id,
                    'account_id': line.prepayment_id.category_id.account_expense_depreciation_id.id,
                    'credit': 0.0,
                    'debit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency.id if company_currency == current_currency else current_currency.id,
                    'amount_currency': line.amount if company_currency != current_currency else 0.0,
                    'date': depreciation_date,
                    'prepayment_id': line.prepayment_id.id,
                })
            ]
            _logger.info(f"Move line values: {vals11}")
            move_id.write({'line_ids': vals11})
            _logger.info(f"Move lines created for move_id: {move_id.id}")

            # --- Force Update Debit/Credit ---
            for move_line in move_id.line_ids:
                if move_line.account_id == line.prepayment_id.category_id.account_prepayment_id:
                    if move_line.credit != amount:
                        _logger.warning(f"Correcting credit for move line {move_line.id}.  Old: {move_line.credit}, New: {amount}")
                        move_line.with_context(check_move_validity=False).write({'credit': amount, 'debit': 0.0})
                elif move_line.account_id == line.prepayment_id.category_id.account_expense_depreciation_id:
                    if move_line.debit != amount:
                        _logger.warning(f"Correcting debit for move line {move_line.id}. Old: {move_line.debit}, New: {amount}")
                        move_line.with_context(check_move_validity=False).write({'debit': amount, 'credit': 0.0})

                _logger.info(
                    f"Move Line ID: {move_line.id}, Account: {move_line.account_id.name}, Debit: {move_line.debit}, Credit: {move_line.credit}"
                )
            # --- End Force Update ---
            line.write({'move_id': move_id.id})
            _logger.info(f"Updated depreciation line with move_id: {move_id.id}")
            created_move_ids.append(move_id.id)

            if can_close:
                _logger.info(f"Setting prepayment state to 'close'. Prepayment ID: {line.prepayment_id.id}")
                line.prepayment_id.write({'state': 'close'})

            _logger.info(f"Finished processing line: {line.name}, sequence: {line.sequence}")

        _logger.info(f"Created move IDs: {created_move_ids}")
        _logger.info("Ending create_move method")
        return {'type': 'ir.actions.act_window_close'}
    
class account_move_line(models.Model):
    _inherit = 'account.move.line'

    prepayment_id = fields.Many2one('account.prepayment', string='Prepayment')
    entry_ids = fields.One2many('account.move.line', 'prepayment_id', string='Entries', states={'draft':[('readonly', False)]})

class account_prepayment_history(models.Model):
    _name = 'account.prepayment.history'
    _description = 'Prepayment history'
    
    name = fields.Char(string='History name', select=1)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    date = fields.Date('Date', required=True, default=time.strftime('%Y-%m-%d'))
    prepayment_id = fields.Many2one('account.prepayment', string='Prepayment', required=True)
    method_time = fields.Selection(selection=[('number', 'Number of Amortizations'), ('end', 'Ending Date')], string='Time Method', required=True,
                              help="The method to use to compute the Dates and number of depreciation lines.\n"\
                                   "Number of amortization: Fix the number of depreciation lines and the time between 2 depreciations.\n" \
                                   "Ending Date: Choose the time between 2 depreciations and the Date the depreciations won't go beyond.")
    method_number = fields.Integer(string='Number of amortization')
    method_period = fields.Integer(string='Period Length', help="Time in month between two depreciations")
    method_end = fields.Date(string='Ending Date')
    note = fields.Text(string='Note')

    _order = 'date desc'
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

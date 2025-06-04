# -*- coding: utf-8 -*-
from odoo import models, fields, _
import logging

_logger = logging.getLogger(__name__)

class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"

    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id')
    stamp_amount = fields.Monetary(string='Stamp Amount', currency_field='currency_id')
    admin_fees = fields.Monetary(string='Admin Fees', currency_field='currency_id')
    withholding_in_amount = fields.Monetary(string='Withholding (IN)', currency_field='currency_id')
    withholding_out_amount = fields.Monetary(string='Withholding (OUT -1)', currency_field='currency_id')
    withholding_out_amount_3 = fields.Monetary(string='Withholding (OUT -3)', currency_field='currency_id')
    advertising_amount = fields.Monetary(string='Advertising Amount', currency_field='currency_id')

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)

        counterpart_line_vals = None
        for vals in line_vals_list:
            if vals['account_id'] == self.destination_account_id.id:
                counterpart_line_vals = vals
                break
        
        if not counterpart_line_vals:
            _logger.error("Could not find counterpart line for payment %s to adjust.", self.name)
            return line_vals_list

        company_currency = self.company_id.currency_id
        payment_currency = self.currency_id
        is_multi_currency = company_currency != payment_currency

        if self.payment_type == 'inbound':
            total_additional_debits_payment_currency = 0.0

            if self.company_id.discount_account and self.discount_amount > 0:
                line_vals_list.append({
                    'name': _('Discount'),
                    'amount_currency': self.discount_amount,
                    'currency_id': payment_currency.id,
                    'debit': payment_currency._convert(self.discount_amount, company_currency, self.company_id, self.date) if is_multi_currency else self.discount_amount,
                    'credit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.discount_account.id,
                    'payment_id': self.id,
                })
                total_additional_debits_payment_currency += self.discount_amount

            if self.company_id.advertising_account and self.advertising_amount > 0:
                line_vals_list.append({
                    'name': _('Advertising'),
                    'amount_currency': self.advertising_amount,
                    'currency_id': payment_currency.id,
                    'debit': payment_currency._convert(self.advertising_amount, company_currency, self.company_id, self.date) if is_multi_currency else self.advertising_amount,
                    'credit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.advertising_account.id,
                    'payment_id': self.id,
                })
                total_additional_debits_payment_currency += self.advertising_amount

            if self.company_id.stamp_account and self.stamp_amount > 0:
                line_vals_list.append({
                    'name': _('Stamp Duty'),
                    'amount_currency': self.stamp_amount,
                    'currency_id': payment_currency.id,
                    'debit': payment_currency._convert(self.stamp_amount, company_currency, self.company_id, self.date) if is_multi_currency else self.stamp_amount,
                    'credit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.stamp_account.id,
                    'payment_id': self.id,
                })
                total_additional_debits_payment_currency += self.stamp_amount

            if self.company_id.withholding_in_account and self.withholding_in_amount > 0:
                line_vals_list.append({
                    'name': _('Withholding (IN)'),
                    'amount_currency': self.withholding_in_amount,
                    'currency_id': payment_currency.id,
                    'debit': payment_currency._convert(self.withholding_in_amount, company_currency, self.company_id, self.date) if is_multi_currency else self.withholding_in_amount,
                    'credit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.withholding_in_account.id,
                    'payment_id': self.id,
                })
                total_additional_debits_payment_currency += self.withholding_in_amount
            
            admin_account = False
            if hasattr(self.company_id, 'admin_fees_account_id') and self.company_id.admin_fees_account_id and self.admin_fees > 0:
                 admin_account = self.company_id.admin_fees_account_id
            elif hasattr(self.company_id, 'admin_fees') and isinstance(self.company_id.admin_fees, models.BaseModel) and self.company_id.admin_fees._name == 'account.account' and self.admin_fees > 0:
                 admin_account = self.company_id.admin_fees
            else:
                 if self.admin_fees > 0:
                     _logger.warning("Admin fees account not configured or 'admin_fees' field on company is not an account.")

            if admin_account and self.admin_fees > 0:
                line_vals_list.append({
                    'name': _('Admin Fees'),
                    'amount_currency': self.admin_fees,
                    'currency_id': payment_currency.id,
                    'debit': payment_currency._convert(self.admin_fees, company_currency, self.company_id, self.date) if is_multi_currency else self.admin_fees,
                    'credit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': admin_account.id,
                    'payment_id': self.id,
                })
                total_additional_debits_payment_currency += self.admin_fees

            if total_additional_debits_payment_currency > 0:
                new_counterpart_amount_currency = counterpart_line_vals['amount_currency'] - total_additional_debits_payment_currency
                counterpart_line_vals['amount_currency'] = new_counterpart_amount_currency
                if new_counterpart_amount_currency >= 0:
                    counterpart_line_vals['debit'] = payment_currency._convert(new_counterpart_amount_currency, company_currency, self.company_id, self.date) if is_multi_currency else new_counterpart_amount_currency
                    counterpart_line_vals['credit'] = 0.0
                else:
                    counterpart_line_vals['credit'] = payment_currency._convert(abs(new_counterpart_amount_currency), company_currency, self.company_id, self.date) if is_multi_currency else abs(new_counterpart_amount_currency)
                    counterpart_line_vals['debit'] = 0.0

        elif self.payment_type == 'outbound':
            total_additional_credits_payment_currency = 0.0

            if self.company_id.withholding_out_account and self.withholding_out_amount > 0:
                line_vals_list.append({
                    'name': _('Withholding (OUT)'),
                    'amount_currency': -self.withholding_out_amount,
                    'currency_id': payment_currency.id,
                    'credit': payment_currency._convert(self.withholding_out_amount, company_currency, self.company_id, self.date) if is_multi_currency else self.withholding_out_amount,
                    'debit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.withholding_out_account.id,
                    'payment_id': self.id,
                })
                total_additional_credits_payment_currency += self.withholding_out_amount

            if self.company_id.withholding_out_account_3 and self.withholding_out_amount_3 > 0:
                line_vals_list.append({
                    'name': _('Withholding (OUT-3)'),
                    'amount_currency': -self.withholding_out_amount_3,
                    'currency_id': payment_currency.id,
                    'credit': payment_currency._convert(self.withholding_out_amount_3, company_currency, self.company_id, self.date) if is_multi_currency else self.withholding_out_amount_3,
                    'debit': 0.0,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': self.company_id.withholding_out_account_3.id,
                    'payment_id': self.id,
                })
                total_additional_credits_payment_currency += self.withholding_out_amount_3
            
            if total_additional_credits_payment_currency > 0:
                new_counterpart_amount_currency = counterpart_line_vals['amount_currency'] + total_additional_credits_payment_currency
                counterpart_line_vals['amount_currency'] = new_counterpart_amount_currency
                if new_counterpart_amount_currency <= 0:
                    counterpart_line_vals['credit'] = payment_currency._convert(abs(new_counterpart_amount_currency), company_currency, self.company_id, self.date) if is_multi_currency else abs(new_counterpart_amount_currency)
                    counterpart_line_vals['debit'] = 0.0
                else:
                    counterpart_line_vals['debit'] = payment_currency._convert(new_counterpart_amount_currency, company_currency, self.company_id, self.date) if is_multi_currency else new_counterpart_amount_currency
                    counterpart_line_vals['credit'] = 0.0
        
        return line_vals_list

    def _prepare_check_values(self, values):
        _logger.info('Preparing check values: %s', values)

        max_debit_value = 0.0
        max_credit_value = 0.0
        max_debit_line = None
        max_credit_line = None

        if self.payment_type == 'outbound' and self.payment_method_code == 'issue_check':
            for line_val in values:
                current_credit = line_val.get('credit', 0)
                if current_credit > max_credit_value:
                    max_credit_value = current_credit
                    max_credit_line = line_val

            if max_credit_line:
                _logger.info('Max credit line for outbound check: %s', max_credit_line)
                # self.do_checks_operations(max_credit_line)

        if self.payment_type == 'inbound' and self.payment_method_code == 'received_third_check':
            for line_val in values:
                current_debit = line_val.get('debit', 0)
                if current_debit > max_debit_value:
                    max_debit_value = current_debit
                    max_debit_line = line_val

            if max_debit_line:
                _logger.info('Max debit line for inbound check: %s', max_debit_line)
                # self.do_checks_operations(max_debit_line)
        return values
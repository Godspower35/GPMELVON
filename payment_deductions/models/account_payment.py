# -*- coding: utf-8 -*-
from odoo import models, fields, _
import logging

_logger = logging.getLogger(__name__)

class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"

    # Inbound Payment Amount Fields
    wht_receivables_inbound_amount = fields.Monetary(string='WHT Receivables', currency_field='currency_id')
    vat_receivables_inbound_amount = fields.Monetary(string='VAT Receivables', currency_field='currency_id')
    wht_payables_inbound_amount = fields.Monetary(string='WHT Payables', currency_field='currency_id')
    ncd_inbound_amount = fields.Monetary(string='NCD', currency_field='currency_id')
    exchange_gain_loss_inbound_amount = fields.Monetary(string='Exchange Gain/Loss', currency_field='currency_id')
    ncd_payables_inbound_amount = fields.Monetary(string='NCD Payables', currency_field='currency_id')
    vat_payables_inbound_amount = fields.Monetary(string='VAT Payables', currency_field='currency_id')

    # Outbound Payment Amount Fields
    wht_receivables_outbound_amount = fields.Monetary(string='WHT Receivables', currency_field='currency_id')
    vat_receivables_outbound_amount = fields.Monetary(string='VAT Receivables', currency_field='currency_id')
    wht_payables_outbound_amount = fields.Monetary(string='WHT Payables', currency_field='currency_id')
    ncd_outbound_amount = fields.Monetary(string='NCD', currency_field='currency_id')
    exchange_gain_loss_outbound_amount = fields.Monetary(string='Exchange Gain/Loss', currency_field='currency_id')
    ncd_payables_outbound_amount = fields.Monetary(string='NCD Payables', currency_field='currency_id')
    vat_payables_outbound_amount = fields.Monetary(string='VAT Payables', currency_field='currency_id')

    def action_draft(self):
        """Reset payment to draft and remove the journal entry so it is regenerated on post."""
        # Remove the move if it exists
        if self.move_id:
            if self.move_id.state in ('posted', 'cancel'):
                try:
                    self.move_id.button_draft()
                except Exception as e:
                    _logger.warning(f"Could not reset move {self.move_id.name} to draft: {e}")
            try:
                self.move_id.unlink()
                _logger.info(f"Deleted move {self.move_id.name} for payment {self.name}")
            except Exception as e:
                _logger.warning(f"Could not delete move {self.move_id.name}: {e}")
        # Now reset payment to draft
        return super().action_draft()

    def action_post(self):
        """Post the payment and ensure journal entry is properly updated"""
        # First, handle the journal entry if it exists and is posted
        if self.move_id and self.move_id.state in ('posted', 'cancel'):
            try:
                self.move_id.button_draft()
                _logger.info(f"Successfully reset move {self.move_id.name} to draft for updating")
            except Exception as e:
                _logger.warning(f"Could not reset move {self.move_id.name} to draft: {e}")
        
        # Clean up existing deduction lines before posting
        if self.move_id and self.move_id.state == 'draft':
            self._cleanup_deduction_lines()
        
        # Call the parent method to post the payment
        result = super().action_post()
        return result

    def _cleanup_deduction_lines(self):
        """Remove existing deduction lines and rebalance the journal entry"""
        if not self.move_id:
            return

        deduction_lines = self.move_id.line_ids.filtered(
            lambda line: line.payment_id == self and 
            line.name in [
                _('WHT Receivables'), _('VAT Receivables'), _('WHT Payables'),
                _('NCD'), _('Exchange Gain/Loss'), _('NCD Payables'), _('VAT Payables')
            ]
        )
        # Find the counterpart line
        counterpart_line = self.move_id.line_ids.filtered(
            lambda line: line.account_id == self.destination_account_id and line.payment_id == self.id
        )
        if deduction_lines:
            try:
                # Calculate the total deduction amounts
                total_deduction_debit = sum(line.debit for line in deduction_lines)
                total_deduction_credit = sum(line.credit for line in deduction_lines)
                total_deduction_amount_currency = sum(line.amount_currency for line in deduction_lines)

                # Remove deduction lines
                deduction_lines.unlink()

                # Restore the counterpart line to its original value
                if counterpart_line:
                    # The original value is the current value plus the deductions (since deductions were subtracted before)
                    new_debit = counterpart_line.debit + total_deduction_debit
                    new_credit = counterpart_line.credit + total_deduction_credit
                    new_amount_currency = counterpart_line.amount_currency + total_deduction_amount_currency

                    counterpart_line.write({
                        'debit': max(new_debit, 0),
                        'credit': max(new_credit, 0),
                        'amount_currency': new_amount_currency,
                    })

                _logger.info(f"Removed {len(deduction_lines)} deduction lines and rebalanced move {self.move_id.name}")

            except Exception as e:
                _logger.warning(f"Could not remove deduction lines from move {self.move_id.name}: {e}")

    def write(self, vals):
        """Override write to handle updates to deduction amounts"""
        deduction_fields = [
            'wht_receivables_inbound_amount', 'vat_receivables_inbound_amount', 
            'wht_payables_inbound_amount', 'ncd_inbound_amount', 
            'exchange_gain_loss_inbound_amount', 'ncd_payables_inbound_amount', 
            'vat_payables_inbound_amount', 'wht_receivables_outbound_amount', 
            'vat_receivables_outbound_amount', 'wht_payables_outbound_amount', 
            'ncd_outbound_amount', 'exchange_gain_loss_outbound_amount', 
            'ncd_payables_outbound_amount', 'vat_payables_outbound_amount'
        ]
        deduction_updated = any(field in vals for field in deduction_fields)
        result = super().write(vals)
        # Only update move if payment is posted and move is not already draft
        if deduction_updated and self.state == 'posted' and self.move_id:
            try:
                if self.move_id.state == 'posted':
                    self.move_id.button_draft()
                if self.move_id.state == 'draft':
                    self._cleanup_deduction_lines()
                    self._synchronize_from_moves([self.move_id])
                    self.move_id.action_post()
                _logger.info(f"Successfully updated journal entry {self.move_id.name} with new deduction amounts")
            except Exception as e:
                _logger.error(f"Error updating journal entry for payment {self.name}: {e}")
                try:
                    if self.move_id.state == 'draft':
                        self.move_id.action_post()
                except:
                    pass
        return result

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

        deduction_lines = []
        deduction_debits = 0.0
        deduction_credits = 0.0
        deduction_amount_currency = 0.0

        def add_deduction(name, amount, account, is_inbound):
            nonlocal deduction_debits, deduction_credits, deduction_amount_currency
            if account is not None and amount != 0:
                is_exchange_gain_loss = 'Exchange Gain/Loss' in name
                debit = credit = amount_currency = 0.0
                if is_inbound:
                    # Inbound: deductions are debits (debit > 0, amount_currency > 0)
                    debit = payment_currency._convert(abs(amount), company_currency, self.company_id, self.date) if is_multi_currency else abs(amount)
                    credit = 0.0
                    amount_currency = abs(amount)
                else:
                    # Outbound: deductions are credits (credit > 0, amount_currency < 0)
                    debit = 0.0
                    credit = payment_currency._convert(abs(amount), company_currency, self.company_id, self.date) if is_multi_currency else abs(amount)
                    amount_currency = -abs(amount)
                # Special handling for Exchange Gain/Loss (keep sign logic as per Odoo standard)
                if is_exchange_gain_loss:
                    if is_inbound:
                        if amount > 0:
                            debit = 0.0
                            credit = payment_currency._convert(amount, company_currency, self.company_id, self.date) if is_multi_currency else amount
                            amount_currency = -abs(amount)
                        else:
                            debit = payment_currency._convert(-amount, company_currency, self.company_id, self.date) if is_multi_currency else -amount
                            credit = 0.0
                            amount_currency = abs(amount)
                    else:
                        if amount > 0:
                            debit = payment_currency._convert(amount, company_currency, self.company_id, self.date) if is_multi_currency else amount
                            credit = 0.0
                            amount_currency = abs(amount)
                        else:
                            debit = 0.0
                            credit = payment_currency._convert(-amount, company_currency, self.company_id, self.date) if is_multi_currency else -amount
                            amount_currency = -abs(amount)
                deduction_lines.append({
                    'name': _(name),
                    'amount_currency': amount_currency,
                    'currency_id': payment_currency.id,
                    'debit': debit,
                    'credit': credit,
                    'date_maturity': self.date,
                    'partner_id': self.partner_id.id,
                    'account_id': account.id,
                    'payment_id': self.id,
                })
                deduction_debits += debit
                deduction_credits += credit
                deduction_amount_currency += amount_currency

        # Inbound deductions
        if self.payment_type == 'inbound':
            add_deduction('WHT Receivables', self.wht_receivables_inbound_amount, self.company_id.wht_receivables_inbound, True)
            add_deduction('VAT Receivables', self.vat_receivables_inbound_amount, self.company_id.vat_receivables_inbound, True)
            add_deduction('WHT Payables', self.wht_payables_inbound_amount, self.company_id.wht_payables_inbound, True)
            add_deduction('NCD', self.ncd_inbound_amount, self.company_id.ncd_inbound, True)
            add_deduction('Exchange Gain/Loss', self.exchange_gain_loss_inbound_amount, self.company_id.exchange_gain_loss_inbound, True)
            add_deduction('NCD Payables', self.ncd_payables_inbound_amount, self.company_id.ncd_payables_inbound, True)
            add_deduction('VAT Payables', self.vat_payables_inbound_amount, self.company_id.vat_payables_inbound, True)
            payment_amount = self.amount
            # Counterpart line: credit > 0, amount_currency < 0
            counterpart_line_vals['amount_currency'] = -abs(payment_amount + deduction_amount_currency)
            if is_multi_currency:
                counterpart_line_vals['credit'] = payment_currency._convert(payment_amount, company_currency, self.company_id, self.date) + deduction_debits - deduction_credits
            else:
                counterpart_line_vals['credit'] = payment_amount + deduction_debits - deduction_credits
            counterpart_line_vals['debit'] = 0.0
        # Outbound deductions
        elif self.payment_type == 'outbound':
            add_deduction('WHT Receivables', self.wht_receivables_outbound_amount, self.company_id.wht_receivables_outbound, False)
            add_deduction('VAT Receivables', self.vat_receivables_outbound_amount, self.company_id.vat_receivables_outbound, False)
            add_deduction('WHT Payables', self.wht_payables_outbound_amount, self.company_id.wht_payables_outbound, False)
            add_deduction('NCD', self.ncd_outbound_amount, self.company_id.ncd_outbound, False)
            add_deduction('Exchange Gain/Loss', self.exchange_gain_loss_outbound_amount, self.company_id.exchange_gain_loss_outbound, False)
            add_deduction('NCD Payables', self.ncd_payables_outbound_amount, self.company_id.ncd_payables_outbound, False)
            add_deduction('VAT Payables', self.vat_payables_outbound_amount, self.company_id.vat_payables_outbound, False)
            payment_amount = self.amount
            # Counterpart line: debit > 0, amount_currency > 0
            counterpart_line_vals['amount_currency'] = abs(payment_amount + deduction_amount_currency)
            if is_multi_currency:
                counterpart_line_vals['debit'] = payment_currency._convert(payment_amount, company_currency, self.company_id, self.date) + deduction_credits - deduction_debits
            else:
                counterpart_line_vals['debit'] = payment_amount + deduction_credits - deduction_debits
            counterpart_line_vals['credit'] = 0.0
        line_vals_list.extend(deduction_lines)
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
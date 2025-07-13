from odoo import models, fields, api
from odoo.tools.misc import format_amount
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    amount_words = fields.Char(compute='_compute_amount_words', store=True)
    amount_total_words = fields.Char(compute='_compute_amount_total_words', store=True)

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_words(self):
        for move in self:
            _logger.info('Computing amount words for move %s', move.id)
            if move.currency_id and move.amount_total:
                move.amount_words = self._format_currency_amount_words(
                    move.amount_total, move.currency_id
                )
                _logger.info('Amount words computed: %s', move.amount_words)
            else:
                move.amount_words = ''
                _logger.info('No amount or currency set for move %s', move.id)

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for move in self:
            _logger.info('Computing total amount words for move %s', move.id)
            if move.currency_id and move.amount_total:
                move.amount_total_words = self._format_currency_amount_words(
                    move.amount_total, move.currency_id
                )
                _logger.info('Total amount words computed: %s', move.amount_total_words)
            else:
                move.amount_total_words = ''
                _logger.info('No total amount or currency set for move %s', move.id)

    def _format_currency_amount_words(self, amount, currency):
        """Format amount in words with proper currency names"""
        _logger.info('Formatting amount %s with currency %s', amount, currency.name)
        
        major_unit = (currency.currency_unit_label or currency.name).upper()
        minor_unit = (currency.currency_subunit_label or 'CENT').upper()
        _logger.info('Using units: major=%s, minor=%s', major_unit, minor_unit)
        
        major_amount = int(amount)
        minor_amount = round((amount - major_amount) * 100)
        _logger.info('Split amount: major=%s, minor=%s', major_amount, minor_amount)
        
        try:
            major_words = num2words(major_amount, lang='en').upper()
            _logger.info('Converted major amount to words: %s', major_words)
        except Exception as e:
            _logger.error('Error converting major amount to words: %s', str(e))
            major_words = str(major_amount)
        
        result = f"{major_words} {major_unit}"
        
        if minor_amount > 0:
            try:
                minor_words = num2words(minor_amount, lang='en').upper()
                _logger.info('Converted minor amount to words: %s', minor_words)
            except Exception as e:
                _logger.error('Error converting minor amount to words: %s', str(e))
                minor_words = str(minor_amount)
            result += f" AND {minor_words} {minor_unit}"
        
        _logger.info('Final formatted result: %s', result)
        return result
from odoo import api, fields, models
from datetime import date

class AccountAsset(models.Model):
    _inherit = 'account.asset'
   
    initial_accumulated_depreciation = fields.Monetary(
        string='Initial Accumulated Depreciation',
        currency_field='currency_id',
        help='Initial accumulated depreciation value before computing new depreciation lines',
        default=0.0,
    )
   
    accumulated_depreciation_value = fields.Monetary(
        string='Accumulated Depreciation Value',
        currency_field='currency_id',
        compute='_compute_accumulated_depreciation_value',
        store=True,
        help='Sum of initial accumulated depreciation and all posted depreciation moves',
    )
   
    current_depreciation_value = fields.Monetary(
        string='Current Depreciation Value',
        currency_field='currency_id',
        compute='_compute_current_depreciation_value',
        store=True,
        help='Total depreciation amount for the current month in the current year',
    )
       
    @api.depends('initial_accumulated_depreciation', 'depreciation_move_ids.state')
    def _compute_accumulated_depreciation_value(self):
        for asset in self:
            posted_amount = sum(
                move.amount_total
                for move in asset.depreciation_move_ids.filtered(
                    lambda m: m.state == 'posted'
                )
            )
            asset.accumulated_depreciation_value = asset.initial_accumulated_depreciation + asset.current_depreciation_value
           
    @api.depends('depreciation_move_ids', 'depreciation_move_ids.state', 'depreciation_move_ids.date', 'prorata_date')
    def _compute_current_depreciation_value(self):
        today = date.today()
        for asset in self:
            if not asset.prorata_date:
                asset.current_depreciation_value = 0.0
                continue
            
            start_month = asset.prorata_date.month
            
            current_year_moves = asset.depreciation_move_ids.filtered(
                lambda m: (
                    m.state == 'posted' and
                    m.date.year == today.year and
                    start_month <= m.date.month <= today.month
                )
            )
            
            current_year_total = sum(move.amount_total for move in current_year_moves)
            
            asset.current_depreciation_value = current_year_total
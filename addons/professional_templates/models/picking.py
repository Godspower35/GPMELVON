# -*- coding: utf-8 -*-
"""
Odoo Proprietary License v1.0.

see License:
https://www.odoo.com/documentation/18.0/legal/licenses.html#odoo-apps
# Copyright ©2024 Bernard K. Too<bernard.too@optima.co.ke>
"""
from odoo import api, fields, models


class PK(models.Model):
    """Inventory model inherited to add more fields and methods for the
    reporting templates module."""

    _inherit = ["stock.picking"]

    pk_style = fields.Many2one(
        "report.template.settings",
        "Picking Style",
        help="Select Style to use when printing the picking slip",
        default=lambda self: self.partner_id.style or self.env.user.company_id.df_style,
    )

    @api.model_create_multi
    def create(self, vals):
        res = super(PK, self).create(vals)
        if res:  # trigger onchage after creating picking to update the partner style
            res.onchange_partner_style()
        return res

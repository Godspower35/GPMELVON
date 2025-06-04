# -*- coding: utf-8 -*-
"""
Odoo Proprietary License v1.0.

see License:
https://www.odoo.com/documentation/18.0/legal/licenses.html#odoo-apps
# Copyright ©2024 Bernard K. Too<bernard.too@optima.co.ke>
"""
from odoo import fields, models


class ReportConfigSettings(models.TransientModel):
    """Transient model to display settings/configs for the report in the
    general settings menu."""

    _inherit = ["res.config.settings"]

    df_style = fields.Many2one(related="company_id.df_style", readonly=False)
    pdf_watermark = fields.Binary(related="company_id.pdf_watermark", readonly=False)
    pdf_watermark_fname = fields.Char(
        related="company_id.pdf_watermark_fname", readonly=False
    )
    pdf_last_page = fields.Binary(related="company_id.pdf_last_page", readonly=False)
    pdf_last_page_fname = fields.Char(
        related="company_id.pdf_last_page_fname", readonly=False
    )

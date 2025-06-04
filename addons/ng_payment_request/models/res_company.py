from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    min_amount = fields.Float(string="Minimum Amount")
    max_amount = fields.Float(string="Maximum Amount")
    plant_manager_limit = fields.Float(string="Plant Manager Payment Request Limit")

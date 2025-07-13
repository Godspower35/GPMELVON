from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    project_title = fields.Char(string='Project Title') 
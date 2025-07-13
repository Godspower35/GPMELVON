from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    is_md = fields.Boolean(string='Is MD', default=False, 
                           help="Check this box if the user is a Managing Director")
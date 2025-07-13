from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_id_prefix = fields.Char(string='Employee ID Prefix', config_parameter='mob_hr_employee_id.prefix')
    employee_id_suffix = fields.Char(string='Employee ID Suffix', config_parameter='mob_hr_employee_id.suffix')
    employee_id_number_padding = fields.Integer(
        string='Number Padding',
        default=2,
        config_parameter='mob_hr_employee_id.number_padding',
        help='Number of digits for the numeric part of the ID'
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['hr.employee'].update_all_employee_ids()

    def action_update_employee_ids(self):
        """Update all employee IDs with the current settings"""
        self.env['hr.employee'].update_all_employee_ids()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'All employee IDs have been updated successfully',
                'sticky': False,
                'type': 'success',
            }
        } 
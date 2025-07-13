from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_identification_id = fields.Char(string='Employee ID', readonly=True, copy=False)

    @api.model
    def _get_id_format_settings(self):
        prefix = self.env['ir.config_parameter'].sudo().get_param('mob_hr_employee_id.prefix', '')
        suffix = self.env['ir.config_parameter'].sudo().get_param('mob_hr_employee_id.suffix', '')
        padding = int(self.env['ir.config_parameter'].sudo().get_param('mob_hr_employee_id.number_padding', '2'))
        return prefix, suffix, padding

    @api.model
    def _generate_unique_employee_id(self):
        prefix, suffix, padding = self._get_id_format_settings()
        
        # Build the search pattern based on configured prefix and suffix
        search_pattern = ''
        if prefix:
            search_pattern += prefix
        search_pattern += '%'
        if suffix:
            search_pattern += suffix

        # Find all IDs matching the pattern
        employees = self.search([('employee_identification_id', 'like', search_pattern)])
        numbers = []
        
        for emp in employees:
            emp_id = emp.employee_identification_id or ''
            if not emp_id:
                continue
                
            # Remove prefix and suffix to get the numeric part
            if prefix:
                emp_id = emp_id[len(prefix):]
            if suffix:
                emp_id = emp_id[:-len(suffix)]
                
            if emp_id.isdigit():
                numbers.append(int(emp_id))

        next_number = max(numbers) + 1 if numbers else 1
        
        # Ensure uniqueness
        while True:
            new_id = f"{prefix}{str(next_number).zfill(padding)}{suffix}"
            if not self.search_count([('employee_identification_id', '=', new_id)]):
                return new_id
            next_number += 1

    @api.model
    def create(self, vals):
        if not vals.get('employee_identification_id'):
            vals['employee_identification_id'] = self._generate_unique_employee_id()
            _logger.info(f"Generated employee ID: {vals['employee_identification_id']}")
        return super(HrEmployee, self).create(vals)

    def action_generate_employee_id(self):
        for rec in self:
            if not rec.employee_identification_id:
                rec.employee_identification_id = self._generate_unique_employee_id()
                _logger.info(f"Generated employee ID for {rec.name}: {rec.employee_identification_id}")

    @api.model
    def update_all_employee_ids(self):
        prefix, suffix, padding = self._get_id_format_settings()
        employees = self.search([], order='id')  # Order by id for consistency
        number = 1
        for emp in employees:
            new_id = f"{prefix}{str(number).zfill(padding)}{suffix}"
            emp.employee_identification_id = new_id
            number += 1 
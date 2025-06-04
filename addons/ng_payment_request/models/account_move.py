from odoo import models, api, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_post(self):
        """Override action_post to preserve debit and credit values"""
        _logger.info(f"Starting action_post override for moves: {self.ids}")
        
        for move in self:
            # Only process draft moves
            if move.state != 'draft':
                _logger.warning(f"Move {move.id} is not in draft state (state: {move.state}), skipping...")
                continue
                
            _logger.info(f"Processing move ID {move.id} with state {move.state}")
            
            # Store values before posting
            stored_lines = {}
            for line in move.line_ids:
                stored_lines[line.id] = {
                    'debit': line.debit,
                    'credit': line.credit
                }
                _logger.info(f"Storing line {line.id}: debit={line.debit}, credit={line.credit}")
            
            # Call standard posting
            try:
                # Call the original method but with super(AccountMove, move) to apply it only to this move
                super(AccountMove, move).action_post()
                _logger.info(f"Move {move.id} posted successfully")
            except Exception as e:
                _logger.error(f"Error posting move {move.id}: {str(e)}")
                raise
            
            # Restore the original values using direct SQL to avoid triggers
            for line_id, values in stored_lines.items():
                _logger.info(f"Restoring line {line_id}: debit={values['debit']}, credit={values['credit']}")
                self.env.cr.execute("""
                    UPDATE account_move_line 
                    SET debit = %s, credit = %s
                    WHERE id = %s
                """, (values['debit'], values['credit'], line_id))
            
            # Force refresh from database 
            self.env.cr.commit()
            
            # Log totals after restore
            total_debit = sum(line.debit for line in move.line_ids)
            total_credit = sum(line.credit for line in move.line_ids)
            _logger.info(f"After restore - Move {move.id}: total_debit={total_debit}, total_credit={total_credit}")
        
        return True
        
    def button_draft(self):
        """Override button_draft to preserve values when moving back to draft"""
        # Store line information before reverting to draft
        stored_lines = {}
        for move in self:
            for line in move.line_ids:
                stored_lines[line.id] = {
                    'debit': line.debit,
                    'credit': line.credit
                }
                
        result = super(AccountMove, self).button_draft()
        
        # Restore values
        for line_id, values in stored_lines.items():
            line = self.env['account.move.line'].browse(line_id)
            if line.exists():
                self.env.cr.execute("""
                    UPDATE account_move_line 
                    SET debit = %s, credit = %s
                    WHERE id = %s
                """, (values['debit'], values['credit'], line_id))
                
        # Force refresh
        self.env.cr.commit()        
        return result
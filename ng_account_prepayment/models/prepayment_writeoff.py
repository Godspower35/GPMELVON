from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PrepaymentWriteoff(models.Model):
    _name = 'prepayment.writeoff'
    _description = 'Prepayment WriteOff'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Corrected inheritance

    write_account = fields.Many2one('account.account', string='Write off Account', required=False, readonly=False, states={'done':[('readonly', True)]})
    write_journal_id = fields.Many2one('account.journal', string='Write off Journal', required=False, readonly=False, states={'done':[('readonly', True)]})
    name = fields.Char(string='Name', required=True, readonly=True, states={'draft':[('readonly', False)]})
    move_id1 = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    account_prepayment_id = fields.Many2one('account.account', string='Prepayment Account', required=False, readonly=False, states={'done':[('readonly', True)]})
    accumulated_value = fields.Float(compute='_compute_accumulated_value', digits=dp.get_precision('Account'), store=True, string='Total Amortized') # use compute instead of deprecated digits_compute
    writeoff_value = fields.Float(string='Writeoff Amount ', digits=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly', False)]}) # use digits instead of deprecated digits_compute
    purchase_value = fields.Float(string='Gross Value ', digits=dp.get_precision('Account'), required=True, readonly=True, states={'draft':[('readonly', False)]})  # use digits instead of deprecated digits_compute
    value_residual = fields.Float(string='Closing Balance', digits=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly', False)]})  # use digits instead of deprecated digits_compute
    user_id = fields.Many2one('res.users', string='Responsible User', required=False, readonly=True, states={'draft':[('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft':[('readonly', False)]}, default=lambda self: self.env.company) # self.env['res.company']._company_default_get('prepayment.writeoff') is deprecated

    date = fields.Date(string='Date', required=True, readonly=True, states={'draft':[('readonly', False)]})
    recompute_prepayment = fields.Boolean(string='Recompute', readonly=False, states={'approve':[('readonly', True)], 'reject':[('readonly', True)], 'cancel':[('readonly', True)]}, help='Tick if you want to upDate the gross value of prepayment and recompute the depreciation with new gross value.')
    state = fields.Selection([('draft', 'New'),
                              ('open', 'Confirmed'),
                              ('approve', 'Approved'),
                              ('done', 'Done'),
                              ('reject', 'Rejected'),
                              ('cancel', 'Cancelled')], string='State',default='draft', required=True,
                              help="When an writeoff is created, the state is 'New'.\n" \
                                   "If the writeoff is confirmed, the state goes in 'Confirmed' \n" \
                                   "If the writeoff is approved, the state goes in 'Approved' \n" \
                                   "If the writeoff is done, the state goes in 'Done' \n" \
                                   "If the writeoff is rejected, the state goes in 'Rejected' \n" \
                                   "If the writeoff is cancelled, the state goes in 'Cancelled' \n" \
                                   , readonly=True)
    allow_partial_writeoff = fields.Boolean(string='Partial Writeoff', help="Tick if you want this prepayment to writeoff partially.", readonly=True, states={'draft':[('readonly', False)]})
    prepayment_id = fields.Many2one('account.prepayment', string='Prepayment', required=True, readonly=True, domain=[('state', '=', 'open')], states={'draft':[('readonly', False)]})


    @api.onchange('prepayment_id')
    def onchange_prepayment(self):
        if self.prepayment_id:
            self.purchase_value = self.prepayment_id.purchase_value
            self.value_residual = self.prepayment_id.value_residual
            self.name = self.prepayment_id.name
            self.account_prepayment_id = self.prepayment_id.category_id.account_prepayment_id.id


    def validate(self):
        self.write({'state': 'open'})

    def approve(self):
        for rec in self:
            if rec.prepayment_id.state in ('draft', 'close'):
                raise UserError( _("You can not approve writeoff of prepayment when related prepayment is in Draft/Close state."))
        self.write({'state': 'approve'})

    def set_to_draft_app(self):
        self.write({'state': 'draft'})

    def set_to_draft(self):
        self.write({'state': 'draft'})

    def set_to_close(self):
        self.write({'state': 'reject'})

    def set_to_cancel(self):
        self.write({'state': 'cancel'})


    @api.depends('prepayment_id.depreciation_line_ids.amount')
    def _compute_accumulated_value(self):
        for rec in self:
            rec.accumulated_value = 0.0
            if rec.prepayment_id:
                for line in rec.prepayment_id.depreciation_line_ids:
                    rec.accumulated_value += line.amount


    def create_move_write(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']  # Not used, can be removed
        created_move_ids = []
        for line in self:
            if any(d.move_id and d.move_id.state == 'draft' for d in line.prepayment_id.depreciation_line_ids):
                raise UserError( _("You can not approve writeoff of prepayment because there are unposted Journals relating this prepayment. Either post or cancel them."))
            if not line.write_journal_id or not line.write_account:
                raise UserError( _("Accounting information missing, please check write off account and write off journal"))
            if line.state == 'done':
                raise UserError( _("Accounting Moves already created."))
            if line.state != 'approve':
                raise UserError( _("Can not create write offs entry in current state."))

            company_currency = line.prepayment_id.company_id.currency_id
            current_currency = line.prepayment_id.currency_id
            # ctx = dict(self._context) # no need for context, use .with_company() or .with_context()
            # ctx.update({'date': line.date})  # Removed, not needed
            # amount = line.prepayment_id.currency_id.with_context(ctx).compute(line.value_residual, line.prepayment_id.company_id.currency_id) #.compute deprecated
            amount = line.value_residual
            if current_currency != company_currency:
              amount = current_currency._convert(amount, company_currency, line.company_id, line.date)


            if line.prepayment_id.category_id.journal_id.type == 'purchase':
                sign = 1
            else:
                sign = -1
            prepayment_name = 'Write offs ' + line.prepayment_id.name
            reference = line.name
            move_vals = {
                'date': line.date,
                'ref': reference,
                'journal_id': line.write_journal_id.id,
            }
            move_id = move_obj.create(move_vals)
            journal_id = line.write_journal_id.id

            move_lines = [
                (0, 0, {
                    'name': prepayment_name,
                    'ref': reference,
                    'move_id': move_id.id,
                    'account_id': line.write_account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'journal_id': journal_id,
                    'partner_id': False,
                    'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and -sign * amount or 0.0,
                    'date': line.date,
                }),
                (0, 0, {
                    'name': prepayment_name,
                    'ref': reference,
                    'move_id': move_id.id,
                    'account_id': line.account_prepayment_id.id,
                    'credit': amount,
                    'debit': 0.0,
                    'journal_id': journal_id,
                    'partner_id': False,
                    'currency_id': company_currency.id != current_currency.id and  current_currency.id or False,
                    'amount_currency': company_currency.id != current_currency.id and sign * amount or 0.0,
                    'analytic_account_id': line.prepayment_id.category_id.account_analytic_id.id,
                    'date': line.date,
                    'prepayment_id': line.prepayment_id.id
                })
            ]

            move_id.write({'line_ids': move_lines})
            created_move_ids.append(move_id)
            #line.write({'move_id1': move_id.id}) # better to use one write call
            #line.write({'state': 'done'})
            #line.prepayment_id.write({'state':'close'}) #better to use one write and call with sudo
            line.write({'move_id1': move_id.id, 'state': 'done'})
            line.prepayment_id.sudo().write({'state':'close'}) # added sudo()
        return True

    def copy(self, default=None):
        default = default or {}
        default.update({'state':'draft', 'move_id1': False})
        return super(PrepaymentWriteoff, self).copy(default)


    def _check_threshold_capitalize(self):
        if self.purchase_value != self.prepayment_id.purchase_value:
            return False
        return True

    _constraints = [
        (_check_threshold_capitalize, 'You can not change the gross value of prepayment in writeoff.', ['purchase_value']),
    ]
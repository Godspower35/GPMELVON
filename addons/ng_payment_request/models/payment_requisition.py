from odoo import fields, models, api, _, exceptions
import logging
_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):

    _inherit = "account.move.line"

    customer_id = fields.Many2one(comodel_name="res.partner", string="Customer/Vendor")


class PaymentRequestLine(models.Model):
    _name = "payment.requisition.line"
    _description = "payment.requisition.line"

    name = fields.Char("Description", required=True)
    approved_amount = fields.Float("Approved Amount")
    payment_request_id = fields.Many2one(
        "payment.requisition", string="Payment Request"
    )
    expense_account_id = fields.Many2one("account.account", "Account")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account"
    )
    requested_amount = fields.Float(string="Requested Amount", store=True)
    state = fields.Char(compute="check_state", string="State")
    partner_id = fields.Many2one("res.partner", string="Customer/Vendor")

    @api.onchange("requested_amount")
    def _get_requested_amount(self):
        if self.requested_amount:
            amount = self.requested_amount
            self.approved_amount = amount


    @api.depends("payment_request_id")
    def check_state(self):
        self.state = self.payment_request_id.state


class PaymentRequest(models.Model):
    _inherit = ["mail.thread"]
    _name = "payment.requisition"
    _description = "Payment Requisition"

    name = fields.Char("Name", default="/", copy=False)
    requester_id = fields.Many2one(
        "res.users", "Requester", required=True, default=lambda self: self.env.user
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account"
    )
    expense_account_id = fields.Many2one("account.account", "Account")
    employee_id = fields.Many2one("hr.employee", "Employee", required=True)
    department_id = fields.Many2one("hr.department", "Department")
    date = fields.Date(string="Date", default=fields.Date.context_today)
    description = fields.Text(string="Description")
    bank_id = fields.Many2one("res.bank", "Bank")
    bank_account = fields.Char("Bank Account", copy=False)
    request_line = fields.One2many(
        "payment.requisition.line", "payment_request_id", string="Lines", copy=False
    )
    partner_id = fields.Many2one("res.partner", string="Customer/Vendor")
    approved_amount = fields.Float(
        compute="_compute_requested_amount", string="Approved Amount", store=True
    )
    requested_amount = fields.Float(compute="_compute_amounts", string="Requested Amount", store=True)
    amount_company_currency = fields.Float(
        compute="_compute_requested_amount",
        string="Amount In Company Currency",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.user.company_id.currency_id.id,
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        default=lambda self: self.env.company.id,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("internal", "Await Internal Control"),
            ("md", "Await MD"),
            ("done", "Approved"),
            ("paid", "Paid"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        tracking=True,
        default="draft",
        string="State",
    )

    need_gm_approval = fields.Boolean(
        "Needs First Approval?", copy=False, readonly=True
    )
    need_md_approval = fields.Boolean(
        "Needs Final Approval?", copy=False, readonly=True
    )
    general_manager_id = fields.Many2one(
        "hr.employee", "General Manager", readonly=True
    )
    manging_director_id = fields.Many2one(
        "hr.employee", "Managing Director", readonly=True
    )
    dept_manager_id = fields.Many2one(
        "hr.employee", "Department Manager", readonly=True
    )
    dept_manager_approve_date = fields.Date(
        "Approved By Department Manager On", readonly=True
    )
    gm_approve_date = fields.Date("First Approved On", readonly=True)
    director_approve_date = fields.Date("Final Approved On", readonly=True)
    move_id = fields.Many2one("account.move", string="Journal Entry")
    journal_id = fields.Many2one("account.journal", string="Journal")
    update_cash = fields.Boolean(
        string="Update Cash Register?",
        readonly=False,
        help="Tick if you want to update cash register by creating cash transaction line.",
    )
    cash_id = fields.Many2one(
        "account.bank.statement",
        string="Cash Register",
        domain=[("journal_id.type", "in", ["cash"]), ("state", "=", "open")],
        required=False,
        readonly=False,
    )
    @api.depends(
        "request_line.approved_amount",
        "currency_id",
        "company_id.currency_id",
        "date"
    )
    def _compute_amounts(self):
        for record in self:
            total_approved_amount = sum(line.approved_amount for line in record.request_line)
            record.approved_amount = total_approved_amount
            record.requested_amount = sum(line.requested_amount for line in record.request_line) # Sum Requested

            if record.company_id.currency_id != record.currency_id:
                record.amount_company_currency = record.currency_id._convert(
                    total_approved_amount, record.company_id.currency_id, record.company_id, record.date or fields.Date.today()
                )
            else:
                record.amount_company_currency = total_approved_amount


    def create(self, vals):
        if not vals.get("name"):
            vals["name"] = self.env["ir.sequence"].next_by_code("payment.requisition")
        return super(PaymentRequest, self).create(vals)

    @api.onchange("requester_id")
    def onchange_requester(self):
        employee = self.env["hr.employee"].search(
            [("user_id", "=", self._uid)], limit=1
        )
        self.employee_id = employee.id
        self.department_id = (
            employee.department_id and employee.department_id.id or False
        )

    def action_confirm(self):
        if not self.request_line:
            raise exceptions.UserError(
                _("Can not confirm request without request lines.")
            )
        body = _(
            "<p>Payment Requisition request %s has been confirmed by <b>%s</b>.</p> <p>Please check and approve.</p>"
            % (self.name, self.env.user.partner_id.name)
        )
        subject = _("Payment Requisition %s" % (self.name,))
        self.notify(
            body, subject, group="ng_payment_request.group_internal"
        )
        return self.write({"state": "internal"})

    def action_internal_approve(self):
        body = _(
            "<p>Payment Requisition request %s has been confirmed by <b>%s</b>.</p> <p>Please check and approve.</p>"
            % (self.name, self.env.user.partner_id.name)
        )
        subject = _("Payment Requisition %s" % (self.name,))
        self.notify(
            body, subject, group="ng_payment_request.group_manager"
        )
        return self.write({"state": "md"})

    def action_md_approve(self):
        body = _(
            "<p>Payment Requisition request %s has been confirmed by <b>%s</b>.</p> <p>Please check and approve.</p>"
            % (self.name, self.env.user.partner_id.name)
        )
        subject = _("Payment Requisition %s" % (self.name,))
        self.notify(
            body, subject, group="account.group_account_invoice"
        )
        return self.write({"state": "done"})

    def notify(self, body, subject, users=None, group=None):
        partner_ids = []
        if group:
            users = self.env.ref(group).users
            for user in users:
                partner_ids.append(user.partner_id.id)
        elif users:
            users = self.env["res.users"].browse(users)
            for user in users:
                partner_ids.append(user.partner_id.id)
        if partner_ids:
            self.message_post(body=body, subject=subject, partner_ids=partner_ids)
        return True

    def action_pay(self):
        move_obj = self.env["account.move"]
        move_line_obj = self.env["account.move.line"]
        statement_line_obj = self.env["account.bank.statement.line"]

        for record in self:
            # Validate journal
            if not record.journal_id:
                raise exceptions.UserError(_("Please select a journal first!"))
                
            company_currency = record.company_id.currency_id
            current_currency = record.currency_id
            
            # Calculate total amount first
            total_amount = sum(line.approved_amount for line in record.request_line)
            _logger.info(f"Processing payment for amount: {total_amount}")
            
            # Partner validation
            partner_id = record.employee_id.user_id.partner_id if record.employee_id.user_id else False
            if not partner_id:
                raise exceptions.UserError(_("Please specify Employee Home Address!"))
                
            # Create move with no lines first
            move_vals = {
                "date": record.date,
                "ref": record.name,
                "journal_id": record.journal_id.id,
                "move_type": "entry",
            }
            move = move_obj.create(move_vals)
            _logger.info(f"Created move with ID: {move.id}")
            
            # Track created line IDs for later update
            debit_line_ids = []
            
            # Create debit lines - store their IDs
            for line in record.request_line:
                if not line.expense_account_id:
                    raise exceptions.UserError(_("Please specify expense account for all lines!"))
                    
                # Create debit line with minimal info
                debit_vals = {
                    "name": record.name,
                    "move_id": move.id,
                    "account_id": line.expense_account_id.id,
                    "partner_id": partner_id.id,
                    "customer_id": line.partner_id.id if line.partner_id else False,
                    "currency_id": current_currency.id,
                    "date": record.date,
                }
                
                debit_line = move_line_obj.with_context(check_move_validity=False).create(debit_vals)
                debit_line_ids.append(debit_line.id)
                _logger.info(f"Created debit line ID: {debit_line.id}")

            # Get payment account
            if hasattr(record.journal_id, 'payment_account_id') and record.journal_id.payment_account_id:
                payment_account_id = record.journal_id.payment_account_id.id
            else:
                payment_account_id = record.journal_id.default_account_id.id
            
            # Create credit line with minimal info
            credit_vals = {
                "name": record.name,
                "move_id": move.id,
                "account_id": payment_account_id,
                "partner_id": partner_id.id,
                "currency_id": current_currency.id,
                "date": record.date,
            }
            
            credit_line = move_line_obj.with_context(check_move_validity=False).create(credit_vals)
            credit_line_id = credit_line.id
            _logger.info(f"Created credit line ID: {credit_line.id}")
            
            # Now force update the debit and credit values directly by ID
            # First calculate the amounts
            total_debit = 0.0
            
            # Update debit lines
            for i, line_id in enumerate(debit_line_ids):
                line = record.request_line[i]
                amount = line.approved_amount
                if current_currency != company_currency:
                    amount = current_currency._convert(
                        amount, company_currency, record.company_id, record.date
                    )
                    
                total_debit += amount
                
                # Force update the debit line
                sql_query = """
                    UPDATE account_move_line 
                    SET debit = %s, credit = 0.0, amount_currency = %s 
                    WHERE id = %s
                """
                self.env.cr.execute(sql_query, (amount, line.approved_amount if current_currency != company_currency else 0.0, line_id))
                _logger.info(f"Executed SQL update for debit line {line_id} with amount {amount}")
            
            # Update credit line
            sql_query = """
                UPDATE account_move_line 
                SET debit = 0.0, credit = %s, amount_currency = %s 
                WHERE id = %s
            """
            credit_amount = total_debit  # Total debit = total credit for balanced entry
            amount_currency = -total_amount if current_currency != company_currency else 0.0
            self.env.cr.execute(sql_query, (credit_amount, amount_currency, credit_line_id))
            _logger.info(f"Executed SQL update for credit line {credit_line_id} with amount {credit_amount}")
            
            # Commit the transaction to ensure SQL updates are persisted
            self.env.cr.commit()
            
            # Reload the move from database to get updated values
            move = move_obj.browse(move.id)
            
            # Verify the values after direct SQL update
            _logger.info("Move line values after direct SQL update:")
            total_debit_check = 0.0
            total_credit_check = 0.0
            for move_line in move.line_ids:
                _logger.info(
                    f"Move Line ID: {move_line.id}, Account: {move_line.account_id.name}, "
                    f"Debit: {move_line.debit}, Credit: {move_line.credit}"
                )
                total_debit_check += move_line.debit
                total_credit_check += move_line.credit
                
            _logger.info(f"Total debit: {total_debit_check}, Total credit: {total_credit_check}")

            # Handle cash register update if needed
            if record.update_cash:
                if record.journal_id.type != "cash":
                    raise exceptions.UserError(_("Journal must be of type 'cash' to update cash register."))
                    
                if not record.cash_id:
                    raise exceptions.UserError(_("Please select a cash register!"))
                    
                statement_line_obj.create({
                    "name": record.name,
                    "amount": -total_amount,
                    "statement_id": record.cash_id.id,
                    "partner_id": partner_id.id,
                    "date": record.date,
                    "PaymentRequest_id": record.id,
                    "payment_ref": record.name,
                })
            
            # Log the final move lines after posting
            _logger.info("Final move line values after posting:")
            for move_line in move.line_ids:
                _logger.info(
                    f"Move Line ID: {move_line.id}, Account: {move_line.account_id.name}, "
                    f"Debit: {move_line.debit}, Credit: {move_line.credit}"
                )
            
            # Update record state and link move
            record.write({
                'state': 'paid',
                'move_id': move.id
            })
            
            _logger.info(f"Successfully processed payment request {record.name} with amount {total_amount}")
        return True
    
    def action_cancel(self):
        self.state = "cancelled"
        return True

    def action_reset(self):
        self.state = "draft"
        return True

    def action_refuse(self):
        self.state = "refused"
        return True


class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    PaymentRequest_id = fields.Many2one("payment.requisition", string="Payment Request")

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'
    approval_rule_id = fields.Many2one('expense.approval.rule', string='Approval Rule')
    approval_line_ids = fields.One2many('expense.approval.line', 'expense_id', string='Approval Lines')
    current_approver_id = fields.Many2one('res.users', string='Current Approver',store=True)
    approval_progress = fields.Float(string='Approval Progress', compute='_compute_approval_progress', store=True)
    requires_approval = fields.Boolean(string='Requires Approval', compute='_compute_requires_approval')

    @api.depends('approval_rule_id', 'approval_line_ids.state')
    def _compute_approval_progress(self):
        for expense in self:
            if not expense.approval_line_ids:
                expense.approval_progress = 0
            else:
                total = len(expense.approval_line_ids)
                approved = len(expense.approval_line_ids.filtered(lambda l: l.state == 'approved'))
                expense.approval_progress = (approved / total) * 100 if total else 0

    @api.onchange('approval_rule_id')
    def _onchange_approval_rule(self):
        for expense in self:
            if expense.approval_rule_id:
                approvers = expense.approval_rule_id.get_approvers_sequence(expense)
                expense.current_approver_id = approvers[0] if approvers else False
                expense._init_approval_lines()

    @api.depends('total_amount')
    def _compute_requires_approval(self):
        for expense in self:
            expense.requires_approval = expense.total_amount > 0

    def action_submit_expenses(self):
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_('Only draft expenses can be submitted.'))

            # Elevate permissions for this specific record
            expense_sudo = expense.sudo()

            # Find the rule
            rule = expense_sudo.approval_rule_id or self.env['expense.approval.rule'].search([
                ('company_id', '=', expense_sudo.company_id.id)
            ], limit=1)

            if not rule:
                raise UserError(_('No approval rule defined for your company.'))

            # Perform all writes and trigger the next steps using the sudo'd record
            expense_sudo.write({
                'approval_rule_id': rule.id,
                'state': 'submit',
            })
            expense_sudo._init_approval_lines()
            expense_sudo._notify_current_approver()
        return True

    def _init_approval_lines(self):
        for expense in self:
            expense.approval_line_ids.unlink()
            approvers = expense.approval_rule_id.sudo().get_approvers_sequence(expense)

            lines = []
            for seq, user in enumerate(approvers, start=1):
                lines.append((0, 0, {
                    'expense_id': expense.id,
                    'approver_id': user.id,
                    'sequence': seq,
                    'state': 'pending',
                }))

            expense.approval_line_ids = lines
            expense.current_approver_id = approvers[0] if approvers else False

    def _notify_current_approver(self):
        for expense in self:
            if expense.current_approver_id:
                expense.message_subscribe(partner_ids=[expense.current_approver_id.partner_id.id])
                expense.message_post(
                    body=_('Expense %s is waiting for your approval.') % expense.name,
                    partner_ids=[expense.current_approver_id.partner_id.id]
                )

    def action_approve_expense(self):
        for expense in self:
            if expense.state != 'submit':
                raise UserError(_('Expense is not waiting for approval.'))

            current_line = expense.approval_line_ids.filtered(
                lambda l: l.approver_id == self.env.user and l.state == 'pending'
            )

            if not current_line:
                raise UserError(_('You are not the current approver or already acted.'))

            current_line.write({'state': 'approved', 'comment': _('Approved')})
            expense._check_approval_progress()

    def action_reject_expense(self):
        for expense in self:
            if expense.state != 'submit':
                raise UserError(_('Expense is not waiting for approval.'))

            current_line = expense.approval_line_ids.filtered(
                lambda l: l.approver_id == self.env.user and l.state == 'pending'
            )

            if not current_line:
                raise UserError(_('You are not the current approver or already acted.'))

            current_line.write({'state': 'rejected', 'comment': _('Rejected')})
            expense.state = 'refused'
            expense.current_approver_id = False
            expense.message_post(
                body=_('Expense rejected by %s') % self.env.user.name
            )

    def _check_approval_progress(self):
        for expense in self:
            approved_lines = expense.approval_line_ids.filtered(lambda l: l.state == 'approved')
            total = len(expense.approval_line_ids)
            approved_count = len(approved_lines)

            # Check if approval rule conditions are met
            rule = expense.approval_rule_id
            if rule and rule.is_approved(expense):
                expense.state = 'approved'
                expense.current_approver_id = False
                expense.message_post(body=_('Expense approved through approval rules.'))
                continue

            # Move to next approver if available
            next_line = expense.approval_line_ids.filtered(
                lambda l: l.state == 'pending' and l.sequence == (approved_count + 1)
            )

            if next_line:
                expense.current_approver_id = next_line.approver_id
                expense._notify_current_approver()
            else:
                # No more approvers and rule not met - reject
                expense.state = 'refused'
                expense.current_approver_id = False

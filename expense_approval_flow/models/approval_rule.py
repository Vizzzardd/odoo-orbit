from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExpenseApprovalRule(models.Model):
    _name = 'expense.approval.rule'
    _description = 'Expense Approval Rule'
    name = fields.Char(string='Rule Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    approver_sequence_ids = fields.One2many('expense.approver.sequence', 'rule_id', string='Approver Sequence')
    percentage_threshold = fields.Float(string='Approval Percentage Threshold', default=60.0)
    specific_approver_id = fields.Many2one('res.users', string='Specific Approver')
    hybrid_rule = fields.Boolean(string='Hybrid Rule', default=False)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('percentage_threshold')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage_threshold < 0 or rec.percentage_threshold > 100:
                raise ValidationError(_('Percentage threshold must be between 0 and 100.'))

    def get_approvers_sequence(self, expense):
        """
        Calculates the full sequence of approvers.
        If the employee's manager is a required first approver,
        they are added at the beginning of the sequence.
        """
        approvers = []
        employee = expense.employee_id

        # Check if the employee's manager exists and is a designated approver
        if employee.parent_id and employee.parent_id.user_id and employee.parent_id.user_id.is_manager_approver:
            manager_user = employee.parent_id.user_id
            if manager_user:
                approvers.append(manager_user)

        # Get the sequence from the rule
        rule_lines = self.approver_sequence_ids.sorted('sequence')
        for user in rule_lines.mapped('approver_id'):
            # Avoid adding the manager twice if they are also in the rule
            if user not in approvers:
                approvers.append(user)

        return approvers

    def is_approved(self, expense):
        approval_lines = expense.approval_line_ids
        total = len(approval_lines)
        if total == 0:
            return False

        approved_lines = approval_lines.filtered(lambda l: l.state == 'approved')

        # Check if the specific approver has approved
        specific_approved = False
        if self.specific_approver_id:
            if self.specific_approver_id in approved_lines.mapped('approver_id'):
                specific_approved = True

        # If it's not a hybrid rule, the specific approver is a hard requirement (auto-approve)
        if not self.hybrid_rule and specific_approved:
            return True

        # Check percentage condition
        percent_approved = (len(approved_lines) / total) * 100
        percentage_met = percent_approved >= self.percentage_threshold

        if self.hybrid_rule:
            # For Hybrid, it's TRUE if EITHER the specific approver OR the percentage is met
            return specific_approved or percentage_met
        else:
            # For non-Hybrid, only the percentage matters at this point
            return percentage_met


class ExpenseApproverSequence(models.Model):
    _name = 'expense.approver.sequence'
    _description = 'Expense Approver Sequence'
    _order = 'sequence'
    rule_id = fields.Many2one('expense.approval.rule', string='Approval Rule', required=True, ondelete='cascade')
    approver_id = fields.Many2one('res.users', string='Approver', required=True,
                                  domain=[('can_approve_expenses', '=', True)])
    sequence = fields.Integer(string='Sequence', required=True)
    _sql_constraints = [
        ('unique_sequence_approver', 'unique(rule_id, sequence)', 'Sequence must be unique per rule.'),
        ('unique_approver_per_rule', 'unique(rule_id, approver_id)', 'Approver must be unique per rule.'),
    ]

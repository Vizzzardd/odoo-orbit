from odoo import models, fields, api,_


class ExpenseApprovalLine(models.Model):
    _name = 'expense.approval.line'
    _description = 'Expense Approval Line'
    _order = 'sequence'
    expense_id = fields.Many2one('hr.expense', string='Expense', required=True, ondelete='cascade')
    approver_id = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    comment = fields.Text(string='Comment')
    approval_date = fields.Datetime(string='Approval Date')
    rejection_date = fields.Datetime(string='Rejection Date')

    def action_approve(self):
        for line in self:
            line.write({
                'state': 'approved',
                'approval_date': fields.Datetime.now(),
                'comment': _('Approved')
            })
            line.expense_id._check_approval_progress()

    def action_reject(self):
        for line in self:
            line.write({
                'state': 'rejected',
                'rejection_date': fields.Datetime.now()
            })
            line.expense_id.state = 'refused'
            line.expense_id.current_approver_id = False


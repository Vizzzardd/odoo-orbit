from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    role = fields.Selection([
        ('employee', 'Employee'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ], string='Role', default='employee')
    manager_id = fields.Many2one('res.users', string='Manager', domain=[('role', '=', 'manager')])
    is_manager_approver = fields.Boolean(string='Is Manager Approver', default=False)
    can_approve_expenses = fields.Boolean(string='Can Approve Expenses', compute='_compute_can_approve_expenses')

    @api.depends('role')
    def _compute_can_approve_expenses(self):
        for user in self:
            user.can_approve_expenses = user.role in ['manager', 'admin']

    @api.constrains('manager_id')
    def _check_manager_role(self):
        for user in self:
            if user.manager_id and user.manager_id.role != 'manager':
                raise ValidationError(_('Manager must have the Manager role.'))

    @api.model
    def create(self, vals):
        user = super().create(vals)

        # Automatically create company if no company exists
        if not self.env['res.company'].search([], limit=1):
            country = user.partner_id.country_id
            if not country:
                try:
                    country = self.env.ref('base.us')
                except ValueError:  # fallback if XML ID doesn't exist
                    country = self.env['res.country'].search([], limit=1)

            company = self.env['res.company'].create({
                'name': f"{user.name}'s Company",
                'country_id': country.id,
            })

            user.write({
                'company_ids': [(4, company.id)],
                'company_id': company.id,
                'role': 'admin',
            })

        return user

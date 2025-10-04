{
    'name': 'Expense Approval Flow Extension',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Multi-level and conditional approval flow for expenses',
    'description': """
        Extends Odoo HR Expense with multi-level approvals,
        conditional rules, and role-based access control.
    """,
    'depends': ['hr_expense', 'mail'],
    'data': [
        'security/expense_approval_flow_security.xml',
        'security/ir.model.access.csv',
        'views/hr_expense_views.xml',
        'views/res_users_views.xml',
        'views/approval_rule_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

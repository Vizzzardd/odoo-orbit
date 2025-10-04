from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'
    default_currency_id = fields.Many2one('res.currency', string='Default Currency', required=True)

    @api.model
    def create(self, vals):
        if 'country_id' in vals and 'default_currency_id' not in vals:
            country = self.env['res.country'].browse(vals['country_id'])
            currency = country.currency_id or self.env.ref('base.USD')
            vals['default_currency_id'] = currency.id
        return super().create(vals)

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_airsi = fields.Boolean(string='AIRSI', default=False)
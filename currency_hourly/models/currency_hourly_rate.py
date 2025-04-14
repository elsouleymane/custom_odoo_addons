from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResCurrencyHourlyRate(models.Model):
    _name = 'res.currency.hourly.rate'
    _description = 'Taux de change horaire'
    _order = 'datetime desc'

    currency_id = fields.Many2one('res.currency', required=True, ondelete='cascade')
    rate = fields.Float(required=True, digits=(12, 6), string="Taux horaire")
    datetime = fields.Datetime(required=True, string="Date et heure")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('uniq_currency_datetime', 'unique(currency_id, datetime, company_id)',
         'Un taux existe déjà pour cette devise, cette heure et cette société.')
    ]

    @api.constrains('rate')
    def _check_rate_positive(self):
        for rec in self:
            if rec.rate <= 0:
                raise ValidationError("Le taux doit être strictement positif.")

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    hourly_rate_ids = fields.One2many(
        'res.currency.hourly.rate',
        'currency_id',
        string="Taux horaires"
    )

    rate_calculation = fields.Selection([
        ('standard', 'Taux standard'),
        ('hourly', 'Taux horaire')
    ], string="Méthode de calcul", default='standard', required=True)

    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        if from_currency.rate_calculation == 'hourly' or to_currency.rate_calculation == 'hourly':
            return self._get_hourly_conversion_rate(from_currency, to_currency, company, date)
        return super()._get_conversion_rate(from_currency, to_currency, company, date)

    def _get_hourly_conversion_rate(self, from_currency, to_currency, company, date):
        # Obtenir le taux horaire le plus proche de la date donnée
        datetime_now = fields.Datetime.now()
        HourlyRate = self.env['res.currency.hourly.rate']

        from_rate = 1.0
        if from_currency.rate_calculation == 'hourly':
            from_rate_rec = HourlyRate.search([
                ('currency_id', '=', from_currency.id),
                ('company_id', '=', company.id),
                ('datetime', '<=', datetime_now)
            ], order='datetime desc', limit=1)
            from_rate = from_rate_rec.rate if from_rate_rec else 1.0
        else:
            from_rate = from_currency.rate

        to_rate = 1.0
        if to_currency.rate_calculation == 'hourly':
            to_rate_rec = HourlyRate.search([
                ('currency_id', '=', to_currency.id),
                ('company_id', '=', company.id),
                ('datetime', '<=', datetime_now)
            ], order='datetime desc', limit=1)
            to_rate = to_rate_rec.rate if to_rate_rec else 1.0
        else:
            to_rate = to_currency.rate

        return to_rate / from_rate


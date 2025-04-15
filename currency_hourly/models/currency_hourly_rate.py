from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResCurrencyHourlyRate(models.Model):
    _name = 'res.currency.hourly.rate'
    _description = 'Taux de change horaire'
    _order = 'datetime desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    currency_id = fields.Many2one('res.currency', required=True, ondelete='cascade')
    rate = fields.Float(required=True, digits=(12, 6), string="Taux direct", compute='_compute_rate',
                        inverse='_inverse_rate', store=True)
    inverse_company_rate = fields.Float(required=True, digits=(12, 6), string="Taux horaire")
    datetime = fields.Datetime(required=True, string="Date et heure")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('uniq_currency_datetime', 'unique(currency_id, datetime, company_id)',
         'Un taux existe déjà pour cette devise, cette heure et cette société.')
    ]

    @api.depends('inverse_company_rate')
    def _compute_rate(self):
        for record in self:
            if record.inverse_company_rate and record.inverse_company_rate != 0:
                record.rate = 1.0 / record.inverse_company_rate
            else:
                record.rate = 0.0

    def _inverse_rate(self):
        for record in self:
            if record.rate and record.rate != 0:
                record.inverse_company_rate = 1.0 / record.rate
            else:
                record.inverse_company_rate = 0.0

    @api.constrains('inverse_company_rate')
    def _check_inverse_rate_positive(self):
        for rec in self:
            if rec.inverse_company_rate <= 0:
                raise ValidationError("Le taux doit être strictement positif.")

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'inverse_company_rate' in init_values:
            return self.env.ref('currency_hourly.mt_hourly_rate_updated')
        return super(ResCurrencyHourlyRate, self)._track_subtype(init_values)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResCurrencyHourlyRate, self).create(vals_list)
        for record in records:
            message = f"""
                    <p><strong>Nouveau taux horaire</strong></p>
                    <ul>
                        <li>Devise : {record.currency_id.name}</li>
                        <li>Taux : {record.inverse_company_rate:.0f} {record.company_id.currency_id.name} pour 1 {record.currency_id.name}</li>
                        <li>Date et heure : {record.datetime.strftime('%d/%m/%Y à %H:%M')}</li>
                    </ul>
                    """
            self.env['mail.message'].create({
                'body': message,
                'model': 'res.currency',
                'res_id': record.currency_id.id,
                'message_type': 'notification',
                'subtype_id': self.env.ref('currency_hourly.mt_hourly_rate_created').id,
            })
        return records

    def write(self, vals):
        old_rates = {}
        old_dates = {}
        if 'inverse_company_rate' in vals:
            old_rates = {record.id: record.inverse_company_rate for record in self}
        if 'datetime' in vals:
            old_dates = {record.id: record.datetime for record in self}

        res = super(ResCurrencyHourlyRate, self).write(vals)

        # Notifications manuelles seulement si des changements significatifs
        for record in self:
            changes = []
            if record.id in old_rates and abs(old_rates[record.id] - record.inverse_company_rate) > 0.01:
                changes.append(f"Taux : {old_rates[record.id]:.0f} → {record.inverse_company_rate:.0f}")
            if record.id in old_dates and old_dates[record.id] != record.datetime:
                old_date_str = old_dates[record.id].strftime('%d/%m/%Y à %H:%M')
                new_date_str = record.datetime.strftime('%d/%m/%Y à %H:%M')
                changes.append(f"Date et heure : {old_date_str} → {new_date_str}")

            if changes:
                message = f"""
                <p><strong>Taux horaire modifié</strong></p>
                <ul>
                    <li>Devise : {record.currency_id.name}</li>
                    <li>{'</li><li>'.join(changes)}</li>
                    <li>Valeur actuelle : {record.inverse_company_rate:.0f} {record.company_id.currency_id.name} pour 1 {record.currency_id.name}</li>
                </ul>
                """
                self.env['mail.message'].create({
                    'body': message,
                    'model': 'res.currency',
                    'res_id': record.currency_id.id,
                    'message_type': 'notification',
                    'subtype_id': self.env.ref('currency_hourly.mt_hourly_rate_updated').id,
                })
        return res

    def unlink(self):
        for record in self:
            message = f"""
                    <p><strong>Taux horaire supprimé</strong></p>
                    <ul>
                        <li>Devise : {record.currency_id.name}</li>
                        <li>Taux : {record.inverse_company_rate:.0f} {record.company_id.currency_id.name} pour 1 {record.currency_id.name}</li>
                        <li>Date et heure : {record.datetime.strftime('%d/%m/%Y à %H:%M')}</li>
                    </ul>
                    """
            self.env['mail.message'].create({
                'body': message,
                'model': 'res.currency',
                'res_id': record.currency_id.id,
                'message_type': 'notification',
                'subtype_id': self.env.ref('currency_hourly.mt_hourly_rate_deleted').id,
            })
        return super(ResCurrencyHourlyRate, self).unlink()


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    rate = fields.Float(tracking=True)
    inverse_company_rate = fields.Float(tracking=True)
    hourly_rate_ids = fields.One2many(
        'res.currency.hourly.rate',
        'currency_id',
        string="Taux horaires",
        tracking=True,
    )
    rate_calculation = fields.Selection([
        ('standard', 'Taux standard'),
        ('hourly', 'Taux horaire')
    ], string="Méthode de calcul", default='standard', required=True, tracking=True)

    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        if from_currency.rate_calculation == 'hourly' or to_currency.rate_calculation == 'hourly':
            return self._get_hourly_conversion_rate(from_currency, to_currency, company, date)
        return super()._get_conversion_rate(from_currency, to_currency, company, date)

    def _get_hourly_conversion_rate(self, from_currency, to_currency, company, date):
        datetime_now = fields.Datetime.now()
        HourlyRate = self.env['res.currency.hourly.rate']

        from_rate = 1.0
        if from_currency.rate_calculation == 'hourly':
            from_rate_rec = HourlyRate.search([
                ('currency_id', '=', from_currency.id),
                ('company_id', '=', company.id),
                ('datetime', '<=', datetime_now)
            ], order='datetime desc', limit=1)
            from_rate = from_rate_rec.inverse_company_rate if from_rate_rec else 1.0
        else:
            from_rate = from_currency.rate or 1.0

        to_rate = 1.0
        if to_currency.rate_calculation == 'hourly':
            to_rate_rec = HourlyRate.search([
                ('currency_id', '=', to_currency.id),
                ('company_id', '=', company.id),
                ('datetime', '<=', datetime_now)
            ], order='datetime desc', limit=1)
            to_rate = to_rate_rec.inverse_company_rate if to_rate_rec else 1.0
        else:
            to_rate = to_currency.inverse_company_rate or 1.0

        return to_rate / from_rate
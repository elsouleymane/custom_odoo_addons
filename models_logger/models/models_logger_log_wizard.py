import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ModelsLoggerWizard(models.TransientModel):
    _name = 'models_logger.log.wizard'
    _description = 'Models Logger Wizard'

    database = fields.Char('Database', default=lambda self: self.env.cr.dbname, readonly=True)
    user_id = fields.Many2one('res.users', string='Username', default=lambda self: self.env.user, required=True)
    password = fields.Char('Mot de passe', required=True)
    model_ids = fields.Many2many('ir.model', string='Models à Tracker')

    result_ids = fields.One2many('models_logger.log.wizard.line', 'wizard_id', string='Historique')

    @api.model
    def _check_password(self, password):
        try:
            user = self.env.user
            user_id = self.env['res.users'].authenticate(self.env.cr.dbname, user.login, password, {})
            return user_id == user.id
        except Exception as e:
            _logger.error("Password verification failed: %s", str(e))
            return False

    def verify_and_track(self):
        self.ensure_one()

        if not self._check_password(self.password):
            raise ValidationError(_('Invalid password for user %s') % self.user_id.name)

        # Track models
        self.result_ids.unlink()

        for model in self.model_ids:
            if not model.model:
                continue

            try:
                model_obj = self.env[model.model]

                query = """
                SELECT DISTINCT
                    partner.name AS creator_name,
                    TO_CHAR(t.create_date, 'YYYY-MM-DD HH24:MI:SS') AS creation_date,
                    TO_CHAR(t.write_date, 'YYYY-MM-DD HH24:MI:SS') AS update_date
                FROM
                    {} t
                LEFT JOIN
                    res_users users ON (t.create_uid = users.id OR t.write_uid = users.id)
                LEFT JOIN
                    res_partner partner ON users.partner_id = partner.id
                WHERE
                    users.id = %s
                LIMIT 10
                """.format(model_obj._table)

                self.env.cr.execute(query, (self.user_id.id,))
                results = self.env.cr.dictfetchall()

                for result in results:
                    self.env['models_logger.log.wizard.line'].create({
                        'wizard_id': self.id,
                        'model_name': model.model,
                        'model_description': model.name,
                        'user_name': result.get('creator_name', 'Unknown'),
                        'database': self.database,
                        'create_date': result.get('creation_date', ''),
                        'write_date': result.get('update_date', '')
                    })

            except Exception as e:
                # Create an error line
                self.env['models_logger.log.wizard.line'].create({
                    'wizard_id': self.id,
                    'model_name': model.model,
                    'model_description': model.name,
                    'user_name': 'Error',
                    'database': self.database,
                    'create_date': '',
                    'write_date': '',
                    'notes': str(e)
                })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tracking Results'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class ModelsLoggerWizardLine(models.TransientModel):
    _name = 'models_logger.log.wizard.line'
    _description = 'Models Logger Wizard Line'

    wizard_id = fields.Many2one('models_logger.log.wizard')
    model_name = fields.Char('Nom du modèle')
    model_description = fields.Char('Description')
    user_name = fields.Char('User')
    database = fields.Char('Database ')
    create_date = fields.Char('Creation Date')
    write_date = fields.Char('Dernière modification')
    notes = fields.Text('Notes')

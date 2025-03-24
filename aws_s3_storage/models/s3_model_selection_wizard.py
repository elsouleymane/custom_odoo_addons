from odoo import models, fields, api


class S3ModelSelectionWizard(models.TransientModel):
    _name = 's3.model.selection.wizard'
    _description = 'S3 Model Selection Wizard'

    config_id = fields.Integer(string='Config ID')
    current_models = fields.Char(string='Models actuellement sélectionnés')
    model_ids = fields.Many2many('ir.model', string='Models à stocker sur S3 Storage')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'model_ids' in fields_list and res.get('current_models'):
            model_ids = [int(id) for id in res['current_models'].split(',') if id.isdigit()]
            res['model_ids'] = model_ids
        return res

    def save_selection(self):
        self.ensure_one()
        model_ids = ','.join([str(model.id) for model in self.model_ids]) if self.model_ids else ''

        self.env['ir.config_parameter'].sudo().set_param('aws_s3_storage.s3_model_ids', model_ids)

        return {'type': 'ir.actions.act_window_close'}

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_s3_cdn = fields.Boolean(
        string='Utiliser S3 pour les Attachments',
        config_parameter='aws_s3_storage.use_s3_cdn'
    )

    amazon_access_key = fields.Char(
        string='AWS Access Key',
        config_parameter='aws_s3_storage.amazon_access_key'
    )

    amazon_secret_key = fields.Char(
        string='AWS Secret Key',
        config_parameter='aws_s3_storage.amazon_secret_key'
    )

    amazon_bucket_name = fields.Char(
        string='S3 Bucket Name',
        config_parameter='aws_s3_storage.amazon_bucket_name'
    )

    amazon_region = fields.Char(
        string='AWS Region',
        default='eu-north-1',
        config_parameter='aws_s3_storage.amazon_region'
    )

    s3_model_ids = fields.Char(
        string='Model IDs for S3 Storage',
        config_parameter='aws_s3_storage.s3_model_ids'
    )

    s3_model_names = fields.Char(
        string='Models for S3 Storage',
        compute='_compute_s3_model_names',
        readonly=True
    )

    @api.depends('s3_model_ids')
    def _compute_s3_model_names(self):
        for record in self:
            names = []
            if record.s3_model_ids:
                model_ids = [int(id) for id in record.s3_model_ids.split(',') if id.isdigit()]
                if model_ids:
                    models = self.env['ir.model'].browse(model_ids).exists()
                    names = models.mapped('name')

            record.s3_model_names = ', '.join(names) if names else 'All Models'

    def action_select_s3_models(self):
        """Open a wizard to select models for S3 storage"""
        self.ensure_one()
        wizard = self.env['s3.model.selection.wizard'].create({
            'config_id': self.id,
            'current_models': self.s3_model_ids or '',
        })

        return {
            'name': 'Select Models for S3 Storage',
            'type': 'ir.actions.act_window',
            'res_model': 's3.model.selection.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_setup_s3_cors(self):
        """Set up CORS configuration for S3 bucket"""
        self.ensure_one()

        if not all([self.amazon_access_key, self.amazon_secret_key,
                    self.amazon_bucket_name, self.amazon_region]):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Error',
                    'message': 'Please fill in all S3 credential fields first',
                    'sticky': False,
                    'type': 'warning',
                }
            }

        try:
            # This would be implemented in a separate model
            self.env['amazon.image.storage'].setup_s3_cors(
                self.amazon_access_key,
                self.amazon_secret_key,
                self.amazon_bucket_name,
                self.amazon_region
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'CORS configuration has been set up successfully',
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to set up CORS: {str(e)}',
                    'sticky': False,
                    'type': 'danger',
                }
            }

from odoo import models, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_s3_cdn = fields.Boolean(string='Use S3 for Product Images',
                              config_parameter='aws_s3_products_img.use_s3_cdn',
                              help='Store attachments in AWS S3 instead of the database'
                                )
    use_s3_attachments = fields.Boolean(string='Use S3 for Product Attachments',
                              config_parameter='aws_s3_products_img.use_s3_attachments')
    amazon_access_key = fields.Char(string='Access Key',
                              config_parameter='aws_s3_products_img.amazon_access_key')
    amazon_secret_key = fields.Char(string='Secret Key',
                              config_parameter='aws_s3_products_img.amazon_secret_key')
    amazon_bucket_name = fields.Char(string='Bucket Name',
                              config_parameter='aws_s3_products_img.amazon_bucket_name')
    amazon_region = fields.Char(string='Amazon Region', config_parameter='aws_s3_products_img.amazon_region')


    def action_setup_s3_cors(self):
        """Setup CORS for S3 bucket"""
        s3_handler = self.env['amazon.product.image']
        result = s3_handler.setup_s3_cors()
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Success"),
                    'message': _("S3 CORS configuration updated successfully"),
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("Failed to update S3 CORS configuration"),
                    'sticky': False,
                    'type': 'danger',
                }
            }
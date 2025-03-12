from odoo import fields, models



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amazon_access_key = fields.Char(string='Amazon S3 Access Key', copy=False,
                                    config_parameter='aws_s3_products_img.amazon_access_key',
                                    help='Enter your Amazon S3 Access Key here.')
    amazon_secret_key = fields.Char(string='Amazon S3 Secret key',
                                    config_parameter='aws_s3_products_img.amazon_secret_key',
                                    help='Enter your Amazon S3 Secret Key here.')
    amazon_bucket_name = fields.Char(string='Folder ID',
                                     config_parameter='aws_s3_products_img.amazon_bucket_name',
                                     help='Enter the name of your Amazon S3 Bucket here.')
    is_amazon_connector = fields.Boolean(
        config_parameter='aws_s3_products_img.amazon_connector', default=False,
        help='Enable or disable the Amazon S3 connector.')

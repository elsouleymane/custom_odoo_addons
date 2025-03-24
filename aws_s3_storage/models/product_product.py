from odoo import models, api, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    use_s3_cdn = fields.Boolean('Use Aws S3 CDN', compute='_compute_use_s3_cdn')
    image_1920_url = fields.Char('Image URL', compute='_compute_s3_image_url')

    @api.depends()
    def _compute_use_s3_cdn(self):
        """Get global setting for S3 CDN usage"""
        use_s3_cdn = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_storage.use_s3_cdn', 'False').lower() == 'true'
        for record in self:
            record.use_s3_cdn = use_s3_cdn

    @api.depends('image_1920')
    def _compute_s3_image_url(self):
        # Get the global setting
        use_s3_cdn = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_storage.use_s3_cdn', 'False').lower() == 'true'

        for record in self:
            record.image_1920_url = False
            if use_s3_cdn and record.image_1920:
                s3_handler = self.env['amazon.product.image']
                url = s3_handler.upload_image_to_s3(record, record.image_1920, 'image_1920')
                if url:
                    record.image_1920_url = url

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        # Get the global setting
        use_s3_cdn = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_storage.use_s3_cdn', 'False').lower() == 'true'

        if use_s3_cdn and 'image_1920' in vals and vals.get('image_1920'):
            s3_handler = self.env['amazon.product.image']
            for record in self:
                s3_handler.upload_image_to_s3(record, record.image_1920, 'image_1920')
        return res

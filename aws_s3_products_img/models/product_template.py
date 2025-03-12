from odoo import models, api, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_s3_cdn = fields.Boolean('Use Aws S3 CDN', default=True)
    image_1920_url = fields.Char('Image URL', compute='_compute_s3_image_url')

    @api.depends('image_1920')
    def _compute_s3_image_url(self):
        for record in self:
            record.image_1920_url = False
            if record.use_s3_cdn and record.image_1920:
                s3_handler = self.env['amazon.product.image']
                url = s3_handler.upload_image_to_s3(record, record.image_1920, 'image_1920')
                if url:
                    record.image_1920_url = url

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if 'image_1920' in vals and vals.get('image_1920') and res.use_s3_cdn:
            s3_handler = self.env['amazon.product.image']
            s3_handler.upload_image_to_s3(res, res.image_1920, 'image_1920')
        return res

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'image_1920' in vals and vals.get('image_1920'):
            for record in self:
                if record.use_s3_cdn:
                    s3_handler = self.env['amazon.product.image']
                    s3_handler.upload_image_to_s3(record, record.image_1920, 'image_1920')
        return res

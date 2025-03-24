from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_s3_storage = fields.Boolean(
        string='Using S3 Storage',
        compute='_compute_use_s3_storage',
        store=False,
    )

    def _compute_use_s3_storage(self):
        """Compute if S3 storage is enabled"""
        use_s3 = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_storage.use_s3_cdn', 'False').lower() == 'true'
        for record in self:
            record.use_s3_storage = use_s3

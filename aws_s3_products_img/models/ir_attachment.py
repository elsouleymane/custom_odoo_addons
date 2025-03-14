from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        # First create the attachments normally
        attachments = super().create(vals_list)

        # Check if S3 is enabled
        use_s3 = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_products_img.use_s3_cdn', 'False').lower() == 'true'

        if use_s3 and not self.env.context.get('skip_attachment_s3'):
            # Upload attachments to S3
            s3_handler = self.env['amazon.product.image']
            for attachment in attachments:
                # Upload to S3 and remove local data
                if attachment.datas:
                    s3_handler.upload_attachment_to_s3(attachment)

        return attachments

    def write(self, vals):
        # Check if we're updating the datas field
        contains_data_update = 'datas' in vals and vals['datas']

        # Normal write operation
        result = super().write(vals)

        # Check if S3 is enabled and we have data changes
        use_s3 = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_products_img.use_s3_cdn', 'False').lower() == 'true'

        if use_s3 and contains_data_update and not self.env.context.get('skip_attachment_s3'):
            s3_handler = self.env['amazon.product.image']
            for attachment in self:
                # Upload to S3 and remove local data
                s3_handler.upload_attachment_to_s3(attachment)

        return result

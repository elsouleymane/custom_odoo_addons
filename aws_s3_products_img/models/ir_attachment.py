from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    use_s3_cdn = fields.Boolean(compute='_compute_use_s3_cdn', store=False)

    @api.depends('res_model')
    def _compute_use_s3_cdn(self):
        """Determine if S3 CDN should be used for this attachment"""
        use_s3 = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.use_s3_cdn', False)
        s3_model_ids_param = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.s3_model_ids', False)

        # Default to not using S3
        for record in self:
            record.use_s3_cdn = False

        if not use_s3:
            return

        # If enabled but no specific models defined, use for all
        if not s3_model_ids_param:
            for record in self:
                record.use_s3_cdn = True
            return

        # Find which models to upload
        try:
            s3_model_ids = [int(id) for id in s3_model_ids_param.split(',') if id.isdigit()]
            if s3_model_ids:
                s3_models = self.env['ir.model'].browse(s3_model_ids).mapped('model')
                for record in self:
                    record.use_s3_cdn = record.res_model in s3_models or not record.res_model
        except Exception as e:
            _logger.error(f"Error computing use_s3_cdn: {e}")
            # In case of error, disable S3
            for record in self:
                record.use_s3_cdn = False

    def _should_store_on_s3(self):
        """Determine if this attachment should be stored on S3"""
        self.ensure_one()
        # Skip if context says to skip S3 (to avoid infinite loops)
        if self.env.context.get('skip_attachment_s3', False):
            return False

        # Check if S3 storage is enabled for this model
        return self.use_s3_cdn

    def write(self, vals):
        """Override write to upload to S3 if needed"""
        # Skip S3 upload if not needed
        if self.env.context.get('skip_attachment_s3') or not vals.get('datas'):
            return super().write(vals)

        # Store temporary data for uploading
        attachments_to_upload = []
        for attachment in self:
            if attachment._should_store_on_s3() and 'datas' in vals:
                # Keep track of attachments and their data for upload after save
                attachments_to_upload.append((attachment.id, vals.get('datas')))

        # Call normal write operation
        result = super().write(vals)

        # Upload relevant attachments to S3
        if attachments_to_upload:
            s3_handler = self.env['amazon.image.storage']  # Updated to use correct model name
            _logger.info(f"Creating {len(attachments_to_upload)} attachments on S3")

            for att_id, temp_data in attachments_to_upload:
                attachment = self.browse(att_id)
                if attachment.exists():
                    # Set data temporarily for upload
                    attachment.with_context(skip_attachment_s3=True).write({'datas': temp_data})
                    # Upload to S3
                    s3_result = s3_handler.upload_attachment_to_s3(attachment)
                    if not s3_result:
                        _logger.warning(f"Failed to upload attachment {att_id} to S3")

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to upload new attachments to S3 if needed"""
        # Call normal create operation
        attachments = super().create(vals_list)

        if self.env.context.get('skip_attachment_s3'):
            return attachments

        # Find attachments that should be on S3
        s3_attachments = attachments.filtered(lambda a: a._should_store_on_s3() and a.datas)

        if s3_attachments:
            s3_handler = self.env['amazon.image.storage']  # Updated to use correct model name
            _logger.info(f"Creating {len(s3_attachments)} new attachments on S3")

            for attachment in s3_attachments:
                # Upload to S3
                s3_result = s3_handler.upload_attachment_to_s3(attachment)
                if not s3_result:
                    _logger.warning(f"Failed to upload new attachment {attachment.id} to S3")

        return attachments

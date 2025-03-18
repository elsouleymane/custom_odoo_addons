from odoo import models, api
import logging
import boto3
from botocore.exceptions import ClientError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _is_product_image(self):
        """Determine if attachment is a product image"""
        if not self.mimetype:
            return False

        # Check if it's an image
        is_image = self.mimetype.startswith('image/')

        return is_image

    def _should_store_on_s3(self):
        """Determine if attachment should be stored on S3"""
        # Product images stay local, other attachments go to S3
        if self.res_model in ['product.template', 'product.product'] and self._is_product_image():
            return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        # Check if S3 is enabled
        use_s3 = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_products_img.use_s3_cdn', 'False').lower() == 'true'

        # Store binary data separately
        temp_binary_data = []

        if use_s3 and not self.env.context.get('skip_attachment_s3'):
            for vals in vals_list:
                if vals.get('datas'):
                    temp_binary_data.append(vals['datas'])
                    # Instead of completely removing data, keep it for local storage
                    if not vals.get('mimetype') or not vals.get('mimetype').startswith('image/'):
                        vals['datas'] = False
                else:
                    temp_binary_data.append(False)

        _logger.info(f"Creating {len(vals_list)} attachments")
        attachments = super().create(vals_list)

        if use_s3 and not self.env.context.get('skip_attachment_s3'):
            s3_handler = self.env['amazon.product.image']

            for i, attachment in enumerate(attachments):
                if temp_binary_data[i]:
                    try:
                        # Only restore data and upload if it's not already there (for non-images)
                        if not attachment.datas and attachment._should_store_on_s3():
                            attachment_with_data = attachment.with_context(skip_attachment_s3=True)
                            attachment_with_data.write({'datas': temp_binary_data[i]})
                            _logger.info(f"Attempting to upload attachment {attachment.id} to S3")
                            s3_handler.upload_attachment_to_s3(attachment_with_data)
                            _logger.info(f"Successfully uploaded attachment {attachment.id} to S3")
                        elif not attachment._should_store_on_s3():
                            _logger.info(f"Keeping product image {attachment.id} local")
                    except Exception as e:
                        _logger.error(f"Failed to upload attachment {attachment.id} to S3: {str(e)}")
                        # Restore data locally if S3 upload fails
                        attachment.with_context(skip_attachment_s3=True).write({'datas': temp_binary_data[i]})

        return attachments

    def write(self, vals):
        use_s3 = self.env['ir.config_parameter'].sudo().get_param(
            'aws_s3_products_img.use_s3_cdn', 'False').lower() == 'true'
        contains_data_update = 'datas' in vals and vals['datas']

        if use_s3 and contains_data_update and not self.env.context.get('skip_attachment_s3'):
            temp_data = vals['datas']

            # Only clear data for non-images that should go to S3
            should_clear = False
            for attachment in self:
                if attachment._should_store_on_s3():
                    should_clear = True
                    break

            if should_clear:
                vals['datas'] = False

            result = super().write(vals)

            s3_handler = self.env['amazon.product.image']
            for attachment in self:
                try:
                    if attachment._should_store_on_s3():
                        attachment.with_context(skip_attachment_s3=True).write({'datas': temp_data})
                        s3_handler.upload_attachment_to_s3(attachment)
                        _logger.info(f"Updated document {attachment.id} on S3")
                    else:
                        # Ensure image data is preserved locally
                        if not attachment.datas:
                            attachment.with_context(skip_attachment_s3=True).write({'datas': temp_data})
                        _logger.info(f"Keeping product image {attachment.id} local")
                except Exception as e:
                    _logger.error(f"Failed to upload attachment {attachment.id} to S3: {str(e)}")
                    # Restore data locally if S3 upload fails
                    attachment.with_context(skip_attachment_s3=True).write({'datas': temp_data})

            return result
        else:
            return super().write(vals)

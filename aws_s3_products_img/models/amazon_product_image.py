import base64
import logging
import boto3
from odoo import models

_logger = logging.getLogger(__name__)


class AmazonProductImage(models.Model):
    _name = 'amazon.product.image'
    _description = 'Amazon Product Image'


    def setup_s3_cors(self):
        """Setup CORS for S3 bucket to allow access from any origin"""
        access_key = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_access_key')
        access_secret = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_secret_key')
        bucket_name = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_bucket_name')
        region = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_region')

        if not all([access_key, access_secret, bucket_name]):
            return False

        try:
            import boto3
            s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=access_secret
            )

            # Configure CORS
            cors_config = {
                'CORSRules': [
                    {
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST'],
                        'AllowedOrigins': ['*'],  # Allow all origins
                        'ExposeHeaders': ['ETag', 'Content-Length'],
                        'MaxAgeSeconds': 3600
                    }
                ]
            }

            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_config
            )
            return True
        except Exception as e:
            _logger.error(f"Failed to setup CORS for S3: {e}")
            return False

    def upload_attachment_to_s3(self, attachment):
                """Upload an attachment to S3 and update its URL"""
                if not attachment.datas:
                    return False

                access_key = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_access_key')
                access_secret = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_secret_key')
                bucket_name = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_bucket_name')
                region = self.env['ir.config_parameter'].sudo().get_param('aws_s3_products_img.amazon_region')

                if not all([access_key, access_secret, bucket_name]):
                    _logger.error("S3 configuration incomplete. Check settings.")
                    return False

                try:
                    s3_client = boto3.client(
                        's3',
                        region_name=region,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=access_secret,
                        config=boto3.session.Config(signature_version='s3v4')
                    )

                    # Get product info if available
                    product_name = 'unnamed'
                    res_id = attachment.res_id or 0

                    if attachment.res_model in ['product.template', 'product.product'] and attachment.res_id:
                        product = self.env[attachment.res_model].browse(attachment.res_id)
                        if product.exists() and product.name:
                            product_name = product.name.lower().replace(' ', '-')
                            product_name = ''.join(c for c in product_name if c.isalnum() or c == '-')[:50]

                    # File name processing
                    file_name = attachment.name or 'unnamed'
                    sanitized_file_name = ''.join(c for c in file_name if c.isalnum() or c in '-._')

                    # S3 key with product info
                    key = f"attachments/{product_name}_{res_id}/{attachment.id}_{sanitized_file_name}"
                    binary_data = base64.b64decode(attachment.datas) if attachment.datas else b''

                    # Upload to S3 with public read access
                    s3_client.put_object(
                        Body=binary_data,
                        Bucket=bucket_name,
                        Key=key,
                        ContentType=attachment.mimetype or 'application/octet-stream',
                        ACL='public-read'
                    )

                    # Generate URL
                    if region:
                        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
                    else:
                        url = f"https://{bucket_name}.s3.amazonaws.com/{key}"

                    # Update attachment URL
                    attachment.with_context(skip_attachment_s3=True).write({
                        'url': url,
                        'datas': False,  # Remove binary data to save space
                    })

                    return url

                except Exception as e:
                    _logger.error(f"Error uploading to S3: {e}")
                    return False
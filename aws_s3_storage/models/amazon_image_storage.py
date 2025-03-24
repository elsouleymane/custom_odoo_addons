import base64
import logging
import boto3
from odoo import models, api, tools

_logger = logging.getLogger(__name__)


class AmazonProductImage(models.Model):
    _name = 'amazon.image.storage'
    _description = 'Amazon s3 Image storage'

    def setup_s3_cors(self):
        """Setup CORS for S3 bucket to allow access from any origin"""
        access_key = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_access_key')
        access_secret = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_secret_key')
        bucket_name = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_bucket_name')
        region = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_region')

        if not all([access_key, access_secret, bucket_name]):
            return False

        try:
            s3_client = boto3.client(
                's3',
                region_name=region or 'eu-north-1',
                aws_access_key_id=access_key,
                aws_secret_access_key=access_secret
            )

            # Configure CORS
            cors_config = {
                'CORSRules': [
                    {
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST'],
                        'AllowedOrigins': ['*'],
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
        _logger.info(f"Starting upload_attachment_to_s3 for attachment {attachment.id}")

        if not attachment.datas or isinstance(attachment.datas, bool):
            _logger.warning(f"Attachment {attachment.id} has no data or data is boolean.")
            return False

        access_key = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_access_key')
        access_secret = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_secret_key')
        bucket_name = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_bucket_name')
        region = self.env['ir.config_parameter'].sudo().get_param('aws_s3_storage.amazon_region')

        if not all([access_key, access_secret, bucket_name]):
            _logger.error("S3 configuration incomplete. Check settings.")
            return False

        try:
            s3_client = boto3.client(
                's3',
                region_name=region or 'eu-north-1',
                aws_access_key_id=access_key,
                aws_secret_access_key=access_secret,
                config=boto3.session.Config(signature_version='s3v4')
            )

            # Get model and record information for folder structure
            model_name = attachment.res_model or 'unclassified'
            record_id = attachment.res_id or 0
            record_name = 'unnamed'

            if attachment.res_model and attachment.res_id:
                try:
                    record = self.env[attachment.res_model].sudo().browse(attachment.res_id)
                    if record.exists():
                        # Try common name fields in order of preference
                        for field in ['name', 'display_name', 'complete_name', 'x_name', 'title']:
                            if hasattr(record, field) and record[field]:
                                record_name = str(record[field])
                                break
                except Exception as e:
                    _logger.warning(f"Couldn't fetch record name: {e}")

            model_folder = model_name.replace('.', '_')
            record_name = record_name.lower().replace(' ', '-')
            record_name = ''.join(c for c in record_name if c.isalnum() or c == '-')[:50]

            file_name = attachment.name or 'unnamed'
            sanitized_file_name = ''.join(c for c in file_name if c.isalnum() or c in '-._')

            key = f"{model_folder}/{record_name}_{record_id}/{attachment.id}_{sanitized_file_name}"

            _logger.info(f"Preparing to upload to key: {key}")

            try:
                binary_data = base64.b64decode(attachment.datas)
                _logger.info(f"Binary data size: {len(binary_data)} bytes")
            except Exception as e:
                _logger.error(f"Error decoding attachment data: {e}")
                return False

            if not binary_data:
                _logger.warning("No binary data to upload")
                return False

            # Upload to S3 with public read access
            s3_client.put_object(
                Body=binary_data,
                Bucket=bucket_name,
                Key=key,
                ContentType=attachment.mimetype or 'application/octet-stream',
                ACL='public-read'
            )

            if region:
                url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
            else:
                url = f"https://{bucket_name}.s3.amazonaws.com/{key}"

            _logger.info(f"Generated S3 URL: {url}")

            attachment.with_context(skip_attachment_s3=True).write({
                'url': url,
                'datas': False,
            })

            _logger.info(f"Successfully uploaded attachment {attachment.id} to S3")
            return url

        except Exception as e:
            _logger.error(f"Error uploading to S3: {e}", exc_info=True)
            return False

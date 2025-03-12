import base64
import logging
import boto3
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AmazonProductImage(models.Model):
    _name = 'amazon.product.image'
    _description = 'Amazon Product Image'

    def upload_image_to_s3(self, product, image_data, image_field):
        try:
            # Fix padding issues with base64 data
            if image_data:
                # Handle both string and bytes formats
                if isinstance(image_data, str):
                    # For string data, ensure proper padding
                    missing_padding = len(image_data) % 4
                    if missing_padding:
                        image_data += '=' * (4 - missing_padding)
                    # Convert to bytes for processing
                    image_bytes = base64.b64decode(image_data)
                elif isinstance(image_data, bytes):
                    # If already bytes, try to decode directly
                    try:
                        image_bytes = base64.b64decode(image_data)
                    except Exception:
                        # If decoding fails, try to convert to string first
                        image_data_str = image_data.decode('utf-8')
                        missing_padding = len(image_data_str) % 4
                        if missing_padding:
                            image_data_str += '=' * (4 - missing_padding)
                        image_bytes = base64.b64decode(image_data_str)
                else:
                    _logger.error(f"Unsupported image data type: {type(image_data)}")
                    return False

                access_key = self.env['ir.config_parameter'].sudo().get_param(
                    'aws_s3_products_img.amazon_access_key')
                access_secret = self.env['ir.config_parameter'].sudo().get_param(
                    'aws_s3_products_img.amazon_secret_key')
                bucket_name = self.env['ir.config_parameter'].sudo().get_param(
                    'aws_s3_products_img.amazon_bucket_name')

                if not all([access_key, access_secret, bucket_name]):
                    _logger.error('Amazon S3 credentials not configured')
                    return False

                # Process the image
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=access_secret
                )

                # Create a key for this image
                model_name = product._name.replace('.', '_')
                key = f"product_images/{model_name}/{product.id}/{image_field}.png"

                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=image_bytes,
                    ContentType='image/png'
                )

                # Return the URL
                return f"https://{bucket_name}.s3.amazonaws.com/{key}"
            return False
        except Exception as e:
            _logger.error(f"Error uploading image to S3: {e}")
            return False

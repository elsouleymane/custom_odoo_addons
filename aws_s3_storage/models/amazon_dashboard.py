import boto3
import os
from odoo import models


class AmazonDashboard(models.Model):
    """
    Amazon dashboard Model to connect with amazon S3
    """
    _name = 'amazon.dashboard'
    _description = "Amazon Dashboard"

    def amazon_view_files(self):
        """
        Fetch all files from s3 and returns it.
        """
        access_key = self.env['ir.config_parameter'].get_param(
            'aws_s3_storage.amazon_access_key')
        access_secret = self.env['ir.config_parameter'].get_param(
            'aws_s3_storage.amazon_secret_key')
        bucket_name = self.env['ir.config_parameter'].get_param(
            'aws_s3_storage.amazon_bucket_name')
        if not access_key or not access_secret or not bucket_name:
            return False
        try:
            client = boto3.client('s3', aws_access_key_id=access_key,
                                  aws_secret_access_key=access_secret)
            region = client.get_bucket_location(Bucket=bucket_name)
            client = boto3.client(
                's3', region_name=region['LocationConstraint'],
                aws_access_key_id=access_key,
                aws_secret_access_key=access_secret
            )
            response = client.list_objects(Bucket=bucket_name)
            file = []
            for data in response['Contents']:
                url = client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': bucket_name, 'Key': data['Key']})
                if data['Size'] == 0:
                    continue
                size_bytes = data['Size'] / 1024
                if size_bytes > 1024:
                    size = str(
                        round(data['Size'] / (1024 * 1024), 1)) + ' MB'
                else:
                    size = str(round(data['Size'] / 1024, 1)) + ' KB'
                file_type = str.upper(
                    os.path.splitext(data['Key'])[1].replace('.', ''))
                file.append(
                    [data['Key'], url, file_type,
                     str(data['LastModified']), size])
            return file
        except Exception as e:
            return ['e', e]

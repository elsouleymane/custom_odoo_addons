
import boto3
from odoo import fields, models
from odoo.exceptions import ValidationError


class AmazonUploadFile(models.TransientModel):
    """
    For opening wizard view
    """
    _name = "amazon.upload.file"
    _description = "Amazon Upload File"

    file = fields.Binary(string="Attachment", help="Select a file to upload")
    file_name = fields.Char(string="File Name",
                            help="Name of the file to upload")

    def action_amazon_upload(self):
        """
        Uploads file to Amazon S3
        """
        attachment = self.env["ir.attachment"].search(
            ['|', ('res_field', '!=', False), ('res_field', '=', False),
             ('res_id', '=', self.id),
             ('res_model', '=', 'amazon.upload.file')])
        try:
            client = boto3.resource(
                's3',
                aws_access_key_id=self.env['ir.config_parameter'].get_param(
                    'amazon_s3_connector.amazon_access_key'),
                aws_secret_access_key=self.env[
                    'ir.config_parameter'].get_param(
                    'amazon_s3_connector.amazon_secret_key'))
            client.Bucket(self.env['ir.config_parameter'].get_param(
                'amazon_s3_connector.amazon_bucket_name')).put_object(
                Key=self.file_name,
                Body=open((attachment._full_path(attachment.store_fname)),
                          'rb'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': 'File has been uploaded successfully. '
                               'Please refresh the page.',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise ValidationError(
                'Failed to Upload Files ( %s .)' % e)

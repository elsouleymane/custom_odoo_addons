

def uninstall_hook(env):
    """
    Deletes System Parameters
    """
    env['ir.config_parameter'].sudo().search(
        [('key', '=', 'aws_s3_products_img.amazon_access_key')]).unlink()
    env['ir.config_parameter'].sudo().search(
        [('key', '=', 'aws_s3_products_img.amazon_secret_key')]).unlink()
    env['ir.config_parameter'].sudo().search(
        [('key', '=', 'aws_s3_products_img.amazon_bucket_name')]).unlink()
    env['ir.config_parameter'].sudo().search(
        [('key', '=', 'aws_s3_products_img.amazon_connector')]).unlink()

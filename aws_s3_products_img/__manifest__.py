{
    'name': "Odoo Amazon S3",
    'version': "1.0",
    'category': "Document Management",

    'description': """This module was developed to upload to Amazon S3 Cloud
                      Storage """,
    'author': 'Nuhu souleymane',
    'website': "https://www.mycompany.com",
    'depends': ['base_setup', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/amazon_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/attachment_views.xml',
        'views/s3_model_selection_wizard_views.xml',
        'wizard/amazon_upload_file_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'aws_s3_products_img/static/src/js/amazon.js',
            'aws_s3_products_img/static/src/js/s3_image_widget.js',
            'aws_s3_products_img/static/src/xml/amazon_dashboard_template.xml',
            'aws_s3_products_img/static/src/xml/s3_image_widget.xml',
            'aws_s3_products_img/static/src/scss/amazon.scss',
            'aws_s3_products_img/static/src/scss/s3_image_widget.scss',
        ]
    },
    'external_dependencies': {'python': ['boto3']},
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'uninstall_hook': 'uninstall_hook'
}
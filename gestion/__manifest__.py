{
    'name': "Gestion",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
    Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

   'license': 'LGPL-3',
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_asset'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'report/asset_immo_report.xml',
        'report/account_payment_report.xml',
        'report/payment_recu_report.xml',
    ],

    'installable': True,
    'application': True,
}

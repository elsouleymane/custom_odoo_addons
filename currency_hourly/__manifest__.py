{
        'name': 'Currency Hourly',
        'version': '1.0',
        'category': 'Accounting/Accounting',
        'summary': 'Mise à jour horaire des taux de change',
        'author': 'Nuhu Souleymane',
        'website': 'https://www.progistack.com',
        'description': """
            Module pour la mise à jour horaire des taux de change des devises.
        """,
        'depends': ['base', 'account', 'mail'],
        'data': [
            'security/ir.model.access.csv',
            'data/mail_data.xml',
            'views/currency_hourly_rate_views.xml',
            'views/res_currency_views.xml',
        ],
        'installable': True,
        'application': False,
        'auto_install': False,
        'license': 'LGPL-3',
    }
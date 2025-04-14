{
        'name': 'Currency Hourly',
        'version': '1.0',
        'category': 'Accounting/Accounting',
        'summary': 'Mise à jour horaire des taux de change',
        'description': """
            Module pour la mise à jour horaire des taux de change des devises.
        """,
        'depends': ['base', 'account'],
        'data': [
            'security/ir.model.access.csv',
            'views/currency_hourly_rate_views.xml',
            'views/res_currency_views.xml',
        ],
        'installable': True,
        'application': False,
        'auto_install': False,
        'license': 'LGPL-3',
    }
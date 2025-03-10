# -*- coding: utf-8 -*-
{
    'name': "Models Tracker",
    'summary': "Track changes in models by user",
    'description': """
        Track and monitor changes in Odoo models.
        Provides user-specific tracking and detailed logs.
    """,
    'license': 'LGPL-3',
    'author': "Nuhu souleymane",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        #'security/ir.model.access.csv',
        'views/models_logger_views.xml',
        'views/models_logger_menus.xml',
        'views/templates.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
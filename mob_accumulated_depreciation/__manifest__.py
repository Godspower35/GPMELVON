# -*- coding: utf-8 -*-
{
    'name': 'Accumulated Depreciation',
    'version': '0.0.2',
    'category': 'Accounting/Assets',
    'summary': 'Adds accumulated depreciation value to assets',
    'description': """
        This module adds:
        - Initial Accumulated Depreciation Value
        - Accumulated Depreciation Value
        - Current Depreciation Value
        to track the total depreciation including posted depreciation lines.
    """,
    'author': 'MOB - Ifeanyi Nneji',
    'website': 'https://www.mattobellonline.com/',
    'depends': ['account_asset'],
    'data': [
        'views/account_asset_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    "images": ["static/description/icon.png"] 

}
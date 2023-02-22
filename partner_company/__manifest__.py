
{
    'name': 'Partner_company',
    'version': '1.6',
    'category': 'Sales/CRM',
    'sequence': 15,
    'summary': 'Track leads and close opportunities',
    'description': "",
    'website': 'https://www.odoo.com/app/crm',
    'depends': [
        'base_setup',
        'sale_management',
        'uom',
        'base',
        'crm',
        'contacts',
    ],
    'data': [

    ],
    'demo': [
    ],
    'css': ['static/src/css/crm.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_qweb': [

        ],
        'web.assets_backend': [

        ],
        'web.assets_tests': [

        ],
        'web.qunit_suite_tests': [

        ],
    },
    'license': 'LGPL-3',
}

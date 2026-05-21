{
    'name': 'Sale Signed Stage',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Add a signed/validated stage before Sale',
    'depends': ['sale_management', 'mail'],
'data': [
        'views/sale_order_signed_views.xml',
    ],

    'installable': True,
    'license': 'LGPL-3',
}


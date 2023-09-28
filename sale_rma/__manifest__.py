# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Sale RMA",
    'summary': """
        Sale RMA""",
    'version': '1.2',
    'category': "Sales/Sales",
    'author':
    'shayma',
    'website': "",
    'depends': [
            'base_setup',
            'sales_team',
            'project',
            ],
    'data': [
        'view/inherit_tast_sale.xml',
    ],
    'demo': [""],
    'development_status': "Beta",
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
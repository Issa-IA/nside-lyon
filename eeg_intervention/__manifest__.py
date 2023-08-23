# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "EEG intervention",
    'summary': """
        Intervention""",
    'version': '1.2',
    'category': "Sales/Sales",
    'author':
    'shayma',
    'website': "",
        'depends': [
        'base_setup',
        'sales_team',
        'utm',
        'contacts',
        'product',
        'sale'
    ],
    'data': [
        "view/intervention_eeg_view.xml",
        "view/etiquette_view.xml",
        "report/Report.xml",
        "report/Etiquettes_barcode.xml",
        "report/bon_livraison.xml",
        "report/box_report.xml",
        "report/test_ok.xml",
    ],
    'demo': [""],
    'development_status': "Beta",
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}

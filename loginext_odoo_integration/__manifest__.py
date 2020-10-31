
{
    'name': 'Loginext-ODOO ERP Integration',
    'version': '1.0',
    'author': 'Prolitus Technologies Pvt. Ltd.',
    'website': 'www.prolitus.com',
    'category': 'Tools & Integration',
    'depends': ['koko_trip_mgmt'],
    'description': """
        Module that integrates the Loginext APIs to ODOO-ERP and get the optimised routes for
        Stove Distributions.
    """,
    'data': [
        'data/loginext_odoo_crons.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

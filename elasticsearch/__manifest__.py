# -*- coding: utf-8 -*-

{
    "name": "Smart search using Elasticsearch",
    "summary": "The module improve the internal search on your odoo website. The module adds search bar suggestions, search speed, on your Odoo website",
    "category": "Website",
    "version": "1.0.0",
    "sequence": 1,
    "author": "Prolitus Technologies Pvt. Ltd.",
    "maintainer": "Prolitus Technologies Pvt. Ltd.",
    "description":
    """Odoo Smart search using Elasticsearch
Use Elasticsearch on Odoo
Improve search speed on odoo website
Odoo website search index
Increase product search on website
Website product search on website
Integrate elasticsearch with Odoo""",
    "depends": [
        'website_sale', 'website', 'emipro_theme_base'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/elastic_server_configuration_view.xml',
        'views/elastic_index_configuration_view.xml',
        'data/demo_data_ec_server.xml',
        'views/elastic_mediator_view.xml',
        'views/elastic_priority_view.xml',
        'data/elastic_cron.xml',
        'views/templates.xml'
    ],
    'qweb': [
        # "static/src/xml/templates.xml",
    ],
    "application": True,
    "installable": True,
}

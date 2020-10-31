# -*- coding: utf-8 -*-

{
    'name': 'MG Approval',
    'version': '1.0',
    'license': 'Other proprietary',
    'summary': """This module allow your employees/users to create Purchase Requisitions.""",
    'description': """
        MG Approval
    """,
    'category': 'Purchase',
    'depends': ['material_purchase_requisitions', 'mg_tender', 'mg_purchase','vendor_portal'],
    'data':[
        'security/procurement_approval_security.xml',
        'security/ir.model.access.csv',
        'data/single_source_sequence.xml',
        'wizard/purchase_action_dashboard_wizard_view.xml',
        'wizard/create_single_source_view.xml',
        'wizard/po_details_wizard_view.xml',
        'wizard/pr_approve_wizard_view.xml',
        'wizard/pr_reject_wizard_view.xml',
        'wizard/pr_withdraw_wizard_view.xml',
        'views/attachment_type_view.xml',
        'views/attachment_status_view.xml',
        'views/purchase_order_view.xml',
        'views/purchase_order2_view.xml',
        'views/procurement_approval_category_view.xml',
        'views/material_purchase_requisition_view.xml',
        'views/material_purchase_requisition2_view.xml',
        'wizard/create_tender_views.xml',
        'views/purchase_requisition_views.xml',
        'views/single_source_configuration_view.xml',
        'views/mg_approval_templates.xml'
    ],
    'installable' : True,
    'application' : False,
}

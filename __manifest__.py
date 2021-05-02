# -*- encoding: utf-8 -*-

{
    'name': 'FEL Mega Print',
    'version': '0.3',
    'category': 'Account',
    'description': """ Integración con factura electrónica de Mega Print """,
    'author': 'Eduardo Cortez Paz',
    'website': 'http://www.exeticsoluciona.com',
    'depends': ['account','l10n_gt_extra'],
    'data': [
        'views/account_view.xml',
        'views/partner_view.xml',
        'views/contigencia.xml',
        'report/reports.xml',
        'report/report_invoice_rsm.xml',
    ],
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

# -*- encoding: utf-8 -*-

{
    'name': 'FEL Mega Print',
    'version': '0.32',
    'category': 'Account',
    'description': """ Integra Odoo y factura electrónica con el CERTIFICADOR Mega Print, Genera DTO locales y DTO locales en contingencia """,
    'author': 'Eduardo Cortez Paz, Allan Ramirez',
    'website': 'https://www.exeticsoluciona.com',
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

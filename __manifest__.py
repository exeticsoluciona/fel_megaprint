{
    'name': 'FEL Mega Print',
    'version': '16.0.1',
    'category': 'Account',
    'description': """ Integra Odoo y factura electrónica con el CERTIFICADOR Mega Print, Genera DTO locales y DTO locales en contingencia """,
    'author': 'Eduardo Cortez Paz, Allan Ramirez',
    'website': 'https://www.exeticsoluciona.com',
    'depends': ['account','l10n_gt_extra','account_accountant'],
    'data': [
        'views/account_view.xml',
        'views/partner_view.xml',
        'views/contigencia.xml',
        'report/reports.xml',
        'report/report_invoice_rsm.xml',
    ],
    'license': 'OPL-1',
    'demo': [],
    'installable': True
}

{
    'name': 'Excel Report',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Excel report generation for project tasks',
    'author': 'Automated Assistant',
    'depends': ['base', 'project', 'eeg_intervention'],
    'data': [
        'report/task_excel_report.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

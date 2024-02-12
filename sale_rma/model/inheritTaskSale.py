from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import timedelta
from odoo.exceptions import ValidationError,Warning

class inheritTask(models.Model):
    _inherit = 'project.task'

    date_from = fields.Datetime('Date de début')
    date_to = fields.Datetime('Date de fin')

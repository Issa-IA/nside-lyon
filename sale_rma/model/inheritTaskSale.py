from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import timedelta
from odoo.exceptions import ValidationError,Warning

class inheritTask(models.Model):
    _inherit = 'project.task'

    date_from = fields.Datetime('Date de début')
    date_to = fields.Datetime('Date de fin')
    URL_INSIDE = "https://inside-lyon-preprod-test-10922170.dev.odoo.com"
    base_url_1 = "https://inside-lyon-preprod-test-10922170.dev.odoo.com/web?#id={}&view_type=form&model=project.task".format(URL, id)

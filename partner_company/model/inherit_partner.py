from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PartnerHerit(models.Model):
    _inherit = 'res.partner'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)




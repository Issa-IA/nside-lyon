from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PartnerHerit(models.Model):
    _inherit = 'res.partner'

    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company_id', store=True)

    @api.depends('ref_company_ids')
    def _compute_company_id(self):
        for partner in self:
            partner.company_id = self.env.company.id if not partner.ref_company_ids else False




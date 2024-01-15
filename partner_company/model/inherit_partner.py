from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PartnerHerit(models.Model):
    _inherit = 'res.partner'

    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self._default_company_id())

    @api.model
    def _default_company_id(self):
        # Si ref_company_ids est vide, utilisez l'entreprise actuelle, sinon, utilisez la première entreprise référencée.
        return self.env.company.id if not self.ref_company_ids else self.ref_company_ids[0].id




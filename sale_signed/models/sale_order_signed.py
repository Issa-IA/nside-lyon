from odoo import fields, models
from odoo.exceptions import UserError


class SaleOrderSignedStage(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('signed', 'Signed'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    def action_mark_validated(self):
        for order in self:
            if order.state in ('sale', 'done'):
                continue
            order.write({'state': 'signed'})

    def action_confirm(self):
        for order in self:
            if order.state != 'signed':
                raise UserError(
                    "Vous devez passer le devis à l’état signé avant de confirmer."
                )
        self.write({'state': 'sale'})
        return True




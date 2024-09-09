from odoo import api, fields, models, exceptions, SUPERUSER_ID, _


class InterventionLineIllisible(models.Model):
    _name = 'intervention.line.illisble'
    _description = 'illisibles'

    # Define fields for the quotation
    etiquette_id = fields.Many2one('model.etiquette', 'Modèle')
    task_id = fields.Many2one('project.task', 'Tâche', compute='_compute_task_id')
    qte_illisible = fields.Integer('Qté Illisible')
    carton_id = fields.Many2one('carton.carton', 'Carton', default=lambda self: self.env['carton.carton'].search([], limit=1), index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    @api.depends('carton_id')
    def _compute_task_id(self):
        for record in self:
            if record.carton_id.task_id:
                record.task_id = record.carton_id.task_id

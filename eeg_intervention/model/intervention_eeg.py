from odoo import api, fields, models, exceptions, SUPERUSER_ID, _


class Composant(models.Model):
    _name = 'composant.model'

    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    product = fields.Many2one('product.product', string='Piles')
    quantity = fields.Float(string='Quantité')


class TaskImage(models.Model):
    _name = 'task.image'
    _description = 'Task Image'

    name = fields.Char("Name")
    image = fields.Binary("Image", attachment=True)
    task_id = fields.Many2one('project.task', string="Task", ondelete='cascade')


class PileModel(models.Model):
    _name = 'pile.model'
    _description = 'Pile'
    
    
    product_id = fields.Many2one('product.product', string='Produit')
    pile_factured = fields.Float(string='Pile Facturée')
    task_id = fields.Many2one('project.task', string='Task')
    pile_non_facture = fields.Float(string='Pile Non Facturée')
    pile_factured_total = fields.Float(string='Total Pile Facturée')


class prestation(models.Model):
    _name = 'prestation.model'

    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    product = fields.Many2one('product.product', string='Prestation')
    quantity = fields.Float(string='Quantité')
    price = fields.Float(string='Price')
    price_total = fields.Float(string='Price total')
    task_id = fields.Many2one('project.task', string='Task')

class EEGRemplacee(models.Model):
    _name = 'eeg.remplacee'
    _description = 'EEG Remplacee'

    task_id = fields.Many2one('project.task', string='Task')
    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    quantity_remplacee = fields.Integer(string='Qte REMPLACEE')
    quantity_hs = fields.Integer(string='Qte HS')
    attente_remplacement = fields.Integer(string='En attente de remplacement', compute='_compute_attente_remplacement')

    @api.depends('quantity_remplacee', 'quantity_hs')
    def _compute_attente_remplacement(self):
        for record in self:
            record.attente_remplacement = record.quantity_hs - record.quantity_remplacee

class InterventionUnique(models.Model):
    _name = 'intervention.unique'
    _description = 'Intervention Unique'

    task_id = fields.Many2one('project.task', string='Task')
    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    quantity_ok = fields.Integer(string='OK')
    quantity_hs = fields.Integer(string='HS')
    quantity_hs_piles = fields.Integer(string='HS Piles')
    quantity_illisible = fields.Integer(string='ILLISIBLE')
    quantity_cassees = fields.Integer(string='CASSEES')
    quantity = fields.Float(string='quantity')

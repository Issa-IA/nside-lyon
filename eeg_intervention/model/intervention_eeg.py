import re
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import timedelta
from odoo.exceptions import ValidationError,Warning


class Composant(models.Model):
    _name = 'composant.model'

    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    product = fields.Many2one('product.product', string='Piles')
    quantity = fields.Float(string='Quantité')
    
class PileModel(models.Model):
    _name = 'pile.model'
    _description = 'Pile'
    
    
    product_id = fields.Many2one('product.product', string='Produit')
    pile_factured = fields.Float(string='Pile Facturée')
    task_id = fields.Many2one('project.task', string='Task')
    pile_non_facture = fields.Float(string='Pile Non Facturée')
    pile_factured_total = fields.Float(string='Total Pile Facturée')



class inheritTask(models.Model):
    _inherit = 'project.task'

    qte_annoncee = fields.Integer(string='Qté annoncées')
    shipping_address = fields.Many2one('res.partner', string='Magasin', index=True, ondelete='cascade')
    contact_store_id = fields.Many2one('res.partner', string='Contact du Magasin', domain="[('parent_id', '=', shipping_address)]")
    qte_recue = fields.Integer(string='Qté reçues')
    qte_non_traitee = fields.Integer(string='Non Traité')
    carton_ids = fields.One2many('carton.carton', 'task_id', string='Cartons')
    cartons_count = fields.Integer(compute='_compute_cartons_count', string='Cartons Count')
    intervention_ids = fields.One2many('intervention.line.eeg', 'task_id', string='Lines')
    intervention_illisible_ids = fields.One2many('intervention.line.illisble', 'task_id', string='Lines Illisible')
    etiquette_count = fields.Integer(compute='_compute_intervention_count', string='Intervention Count')
    sequence1 = fields.Char(string='Dossier N°', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('project.tasksequence'))
    num_cartons_client = fields.Integer(string='Nombre de carton ICR', compute='_compute_num_cartons_client')
    pile_factured_total = fields.Float(string='Total Pile Facturée')
    sale_order__intervention_id = fields.Many2one('sale.order', string='Commande intervention', store=True)
    @api.depends('carton_ids')
    def _compute_num_cartons_client(self):
        for task in self:
            num_cartons_client = len(task.carton_ids.filtered(lambda carton: carton.proprietaire_carton == 'ICR'))
            task.num_cartons_client = num_cartons_client
            
    Total_illisible = fields.Integer(string='Total ILLISIBLES', compute='calcul_total_illisible')
    transport_type = fields.Selection([('palette', 'Palette'),('carton', 'Carton')], string='Transport', default='carton', readonly=False, compute='_compute_proprietaire_type')
    num_palette = fields.Integer(string='Quantité palette')
    @api.depends('cartons_count')
    def _compute_proprietaire_type(self):
        for record in self:
            if record.cartons_count > 7:
                record.transport_type = 'palette'
            else:
                record.transport_type = 'carton'

    piles_ids = fields.One2many('pile.model', 'task_id', string='Piles', compute='_compute_piles_ids', store=True)
    
    
    
    @api.depends('intervention_ids.etiquette_id', 'intervention_ids.pile_test', 'intervention_ids.test', 'intervention_ids.affichage_defectueux', 'intervention_ids.code_erreur', 'intervention_ids.activation', 'intervention_ids.piles', 'intervention_ids.esthetique', 'intervention_ids.cassees', 'intervention_ids.illisible')
    def _compute_piles_ids(self):
        for task in self:
            piles_by_etiquette = {}
    
            # Supprimer toutes les lignes existantes dans piles_ids
            task.piles_ids.unlink()
    
            for intervention in task.intervention_unique_ids:
                etiquette_id = intervention.etiquette_id
                if etiquette_id not in piles_by_etiquette:
                    piles_by_etiquette[etiquette_id] = {
                        'pile_factured_total': 0.0,
                        'pile_lines': {},
                    }
    
                for composant in etiquette_id.composant_ids:
                    product_id = composant.product.id
                    quantity_used = int(composant.quantity) * int(intervention.quantity_ok)
                    used_non_facturee = int(composant.quantity) * int(intervention.quantity_hs_piles)
    
                    if product_id not in piles_by_etiquette[etiquette_id]['pile_lines']:
                        piles_by_etiquette[etiquette_id]['pile_lines'][product_id] = {
                            'product_id': product_id,
                            'pile_factured': 0,
                            'pile_non_facture': 0,
                        }
    
                    piles_by_etiquette[etiquette_id]['pile_lines'][product_id]['pile_factured'] += quantity_used
                    piles_by_etiquette[etiquette_id]['pile_lines'][product_id]['pile_non_facture'] += used_non_facturee
    
                    piles_by_etiquette[etiquette_id]['pile_factured_total'] += quantity_used
    
            piles = []
            for etiquette_id, data in piles_by_etiquette.items():
                pile_lines = list(data['pile_lines'].values())
                pile_factured_total = data['pile_factured_total']
    
                piles.extend(pile_lines)
    
            task.piles_ids = [(0, 0, line) for line in piles]
            task.pile_factured_total = sum(data['pile_factured_total'] for data in piles_by_etiquette.values())

    @api.depends('intervention_ids.etiquette_id', 'intervention_ids.pile_test', 'intervention_ids.test','intervention_ids.affichage_defectueux', 'intervention_ids.code_erreur', 'intervention_ids.activation', 'intervention_ids.piles', 'intervention_ids.esthetique', 'intervention_ids.cassees', 'intervention_ids.illisible')
    def _compute_intervention_unique_ids(self):
        for task in self:
            unique_interventions = task.intervention_ids.filtered(
                lambda line: line.etiquette_id and (line.pile_test or line.test or line.code_erreur or line.affichage_defectueux or line.activation or line.piles or line.esthetique or line.cassees or line.illisible))
            quantity_dict = {} 
    
            for line in unique_interventions:
                etiquette_id = line.etiquette_id
                quantity_ok = line.pile_test + line.test
                quantity_hs = line.code_erreur + line.affichage_defectueux + line.activation + line.piles
                quantity_hs_piles = line.piles
                quantity_cassees = line.esthetique + line.cassees
                quantity_illisible = line.illisible
                quantity = quantity_ok + quantity_hs + quantity_cassees + quantity_illisible
    
                if etiquette_id in quantity_dict:
                    quantity_dict[etiquette_id]['quantity_ok'] += quantity_ok
                    quantity_dict[etiquette_id]['quantity_hs'] += quantity_hs
                    quantity_dict[etiquette_id]['quantity_hs_piles'] += quantity_hs_piles
                    quantity_dict[etiquette_id]['quantity_cassees'] += quantity_cassees
                    quantity_dict[etiquette_id]['quantity_illisible'] += quantity_illisible
                    quantity_dict[etiquette_id]['quantity'] += quantity
                    
                else:
                    quantity_dict[etiquette_id] = {
                        'quantity_ok': quantity_ok,
                        'quantity_hs': quantity_hs,
                        'quantity_hs_piles' : quantity_hs_piles,
                        'quantity_cassees': quantity_cassees,
                        'quantity_illisible': quantity_illisible,
                        'quantity' : quantity
                    }
    
            unique_intervention_lines = self.env['intervention.line.eeg']
    
            for etiquette_id, quantities in quantity_dict.items():
                unique_intervention_lines += self.env['intervention.line.eeg'].new({
                    'etiquette_id': etiquette_id.id,
                    'quantity_ok': quantities['quantity_ok'],
                    'quantity_hs': quantities['quantity_hs'],
                    'quantity_hs_piles' : quantities['quantity_hs_piles'],
                    'quantity_cassees': quantities['quantity_cassees'],
                    'quantity_illisible': quantities['quantity_illisible'],
                    'quantity': quantities['quantity'],
                })
    
            task.intervention_unique_ids = [(5, 0, 0)] + [
                (0, 0, {'etiquette_id': line.etiquette_id.id, 'quantity_ok': line.quantity_ok,'quantity': line.quantity,'quantity_hs_piles':line.quantity_hs_piles, 'quantity_hs': line.quantity_hs, 'quantity_cassees': line.quantity_cassees, 'quantity_illisible': line.quantity_illisible}) for line in
                unique_intervention_lines]

       
    @api.depends('intervention_ids')
    def _compute_intervention_count(self):
        for record in self:
            record.etiquette_count = len(record.intervention_ids)

    @api.depends('carton_ids')
    def _compute_cartons_count(self):
        for record in self:
            record.cartons_count = len(record.carton_ids)

    def calcul_total_illisible(self):
        for rec in self.carton_ids:
            rec.Total_illisible = rec.total_illisible

    def action_open_related_cartons(self):
        return {
            'name': 'Cartons',
            'type': 'ir.actions.act_window',
            'res_model': 'carton.carton',
            'domain': [('task_id', '=', self.id)],
            'context': {'search_default_task_id': self.id,'default_task_id': self.id},
            'view_mode': 'tree,form',
        }

    def action_open_related_etiquettes(self):
        return {
            'name': 'EEG',
            'type': 'ir.actions.act_window',
            'res_model': 'intervention.line.eeg',
            'domain': [('task_id', '=', self.id)],
            'context': {'search_default_task_id': self.id,'default_task_id': self.id},
            'view_mode': 'tree,form',
        }
        
    @api.model
    def generate_report(self):
        report = self.env.ref('project.task.fiche_suivie')
        report_data = report.render_qweb([self.id])[0]

        self.message_post(
            body="Here is the automatically generated report.",
            subject="Auto-generated Report",
            attachment_ids=[(0, 0, {
                'name': 'fiche.pdf',
                'datas': report_data,
            })]
        )

    @api.model
    def generate_report_bon_livraison(self):
        report = self.env.ref('project.task.bon_livraison')
        report_data = report.render_qweb([self.id])[0]

        self.message_post(
            body="Here is the automatically generated report.",
            subject="Auto-generated Report",
            attachment_ids=[(0, 0, {
                'name': 'fiche.pdf',
                'datas': report_data,
            })]
        )

    prestation_ids = fields.One2many('prestation.model', 'task_id', string='Prestations', compute='create_prestation_lines')
    intervention_unique_ids = fields.One2many('intervention.unique', 'task_id', string='Interventions Unique', compute='_compute_intervention_unique_ids', store=True)
    transport_product_carton= fields.Many2one('product.product', string='Transport product Carton', default=4252)
    transport_product_palette= fields.Many2one('product.product', string='Transport product palette', default=5711)
    product_carton= fields.Many2one('product.product', string='Product carton', default=5293)
    
    @api.onchange('intervention_unique_ids')
    def _onchange_intervention_unique_ids(self):
        pass


    @api.depends('intervention_unique_ids')
    def create_prestation_lines(self):
        prestation_obj = self.env['prestation.model']  
        prestation_ids = self.env['prestation.model'] 

        for record in self.intervention_unique_ids:
            etiquette_id = record.etiquette_id
            quantity = record.quantity - record.quantity_cassees

            liste_de_prix = etiquette_id.marque_id.pricelist_id  

            if liste_de_prix:
                for item in liste_de_prix.item_ids:
                    price = item.fixed_price
                    product = item.product_id

                    existing_line = prestation_ids.filtered(
                        lambda line: line.product == product and line.price == price)

                    if existing_line:
                        existing_line.quantity += quantity
                    else:
                        prestation_ids |= prestation_obj.create({
                            'etiquette_id': etiquette_id.id,
                            'product': product.id,
                            'price': price,
                            'price_total': price * quantity,
                            'task_id': self.id, 
                            'quantity': quantity, 
                            
                        })

        self.prestation_ids = prestation_ids

   
    @api.depends('intervention_ids.etiquette_id')
    def _compute_interventions(self):
        for task in self:
            unique_etiquettes = task.intervention_ids.mapped('etiquette_id')
            task.intervention_ids = [(6, 0, unique_etiquettes.ids)]

    def create_sale_order(self):
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']
    
        for task in self:
            num_cartons_client = task.num_cartons_client
            
            order = SaleOrder.create({
                'partner_id': task.partner_id.id,
            })
            task.sale_order__intervention_id = order.id

            order_lines_by_product = {}
            for intervention in task.intervention_unique_ids:
                for component in intervention.etiquette_id.composant_ids:
                    product_id = component.product.id
    
                    if product_id in order_lines_by_product:
                        order_line = SaleOrderLine.browse(order_lines_by_product[product_id])
                        order_line.product_uom_qty += component.quantity * intervention.quantity_ok
                    else:
                        order_line = SaleOrderLine.create({
                            'order_id': order.id,
                            'product_id': product_id,
                            'product_uom_qty': component.quantity * intervention.quantity_ok,
                            'price_unit': component.product.list_price,
                        })
                        order_lines_by_product[product_id] = order_line.id
    
            order_lines_by_service = {}
    
            for service in task.prestation_ids:
                product_id = service.product.id
    
                if product_id in order_lines_by_service:
                    order_line = SaleOrderLine.browse(order_lines_by_service[product_id])
                    order_line.product_uom_qty += service.quantity
                else:
                    order_line = SaleOrderLine.create({
                        'order_id': order.id,
                        'product_id': product_id,
                        'product_uom_qty': service.quantity,
                        'price_unit': service.price,
                    })
                    order_lines_by_service[product_id] = order_line.id
                    
            # ligne pour product_carton_transport
            if task.transport_type == 'carton' and task.transport_product_carton:
                SaleOrderLine.create({
                    'order_id': order.id,
                    'product_id': task.transport_product_carton.id,
                    'product_uom_qty': num_cartons_client,
                    'price_unit': task.transport_product_carton.list_price,
                })
            
            # ligne pour product_carton
            if task.product_carton:
                SaleOrderLine.create({
                    'order_id': order.id,
                    'product_id': task.product_carton.id,
                    'product_uom_qty': num_cartons_client,
                    'price_unit': task.product_carton.list_price,
                })
              # ligne pour product_palette_transport  
            if task.transport_type == 'palette' and task.transport_product_palette and task.num_palette > 0:
                SaleOrderLine.create({
                    'order_id': order.id,
                    'product_id': task.transport_product_palette.id,
                    'product_uom_qty': task.num_palette,
                    'price_unit': task.transport_product_palette.list_price,
                    })
         
class prestation(models.Model):
    _name = 'prestation.model'

    etiquette_id = fields.Many2one('model.etiquette', string='Etiquette')
    product = fields.Many2one('product.product', string='Prestation')
    quantity = fields.Float(string='Quantité')
    price = fields.Float(string='Price')
    price_total = fields.Float(string='Price total')
    task_id = fields.Many2one('project.task', string='Task')


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


class ModelCarton(models.Model):
    _name = 'model.carton'
    _description ='Modèle carton'

    # Define fields for the quotation
    name = fields.Text(string='Type')
    largeur_carton = fields.Float(
        string="Largeur",
        digits='Largeur', default=0.0,
        store=True, readonly=False, required=True)
    hauteur_carton = fields.Float(
        string="Hauteur",
        digits='Hauteur carton', default=0.0,
        store=True, readonly=False, required=True)
    longueur_carton = fields.Float(
        string="Longueur",
        digits='Longueur carton', default=0.0,
        store=True, readonly=False, required=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)



class MarqueEtiquette(models.Model):
    _name = 'marque.etiquette'
    _description = 'Marque Etiquette'

    name = fields.Text(string='Marque')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Liste des prix')


class ModelEtiquette(models.Model):
    _name = 'model.etiquette'
    _description ='Modèle Etiquette'

    # Define fields for the quotation
    name = fields.Text(string='Etiquette')
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True)
    marque_id = fields.Many2one('marque.etiquette', string='Marque', create=True)
    composant_ids = fields.One2many('composant.model', 'etiquette_id', string='Composants')
    user_id = fields.Many2one(
        'res.users', string='Opened By',
        required=True,
        index=True,
        readonly=True,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    @api.depends('marque_id.name')
    def _compute_display_name(self):
        for names in self:
            if names.marque_id:
                names.display_name = "[%s] %s" % (names.marque_id.name, names.name)
            else:
                names.display_name = names.name
            



class Carton(models.Model):
    _name = 'carton.carton'
    _description ='Cartons'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    # Define fields for the quotation
    name = fields.Text(string='Carton N°')
    model_carton = fields.Many2one('model.carton', 'Modèle')
    nb_carton = fields.Integer(string='Nombre carton')
    transporteur = fields.Selection([
        ('UPS', 'UPS'),
        ('TRANSALDIS', 'TRANSALDIS')
    ])
    nb_palette = fields.Integer(string='Nombre palette')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    user_id = fields.Many2one(
        'res.users', string='Opened By',
        required=True,
        index=True,
        readonly=True,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    poids_carton = fields.Float(
        string="Poids",
        digits='Poids carton', default=0.0,
        store=True, readonly=False)
    proprietaire_carton =  fields.Selection([
        ('CLIENT', 'CLIENT'),
        ('ICR', 'ICR')
    ])
    task_id = fields.Many2one('project.task','Tâche', default=lambda self: self._get_default_task(), index=True, copy=False)
    date_expedition = fields.Date(string="Date d'expédition", tracking=True)

    def _get_default_task(self):
    # Récupérer l'enregistrement Étiquette actuellement actif
        active_etiquette = self.env.context.get('self.id')
        
        if active_etiquette:
            # Récupérer la valeur du champ task_id de l'enregistrement Étiquette actif
            etiquette = self.env['intervention.line.eeg'].browse(active_etiquette)
            return etiquette.task_id.id if etiquette.task_id else False
    
        # Si aucun enregistrement Étiquette actif n'est trouvé, renvoyer False
        return False
    
    intervention_line_eeg_ids = fields.One2many('intervention.line.eeg', 'carton_id', string='Lines')
    intervention_line_illisible_ids = fields.One2many('intervention.line.illisble', 'carton_id', string='Lines')
    total_ok = fields.Integer(string='Total OK', compute='calcul_total_ok')
    total_hs = fields.Integer(string='Total HS', compute='calcul_total_hs')
    total_illisible = fields.Integer(string='Total Illisible',  compute='calcul_total_illisibles')
    total_casse = fields.Integer(string='Total cassée', compute='calcul_total_cassee')
    
    @api.depends('intervention_line_illisible_ids.qte_illisible')
    def calcul_total_illisibles(self):
        for rec in self:
            selected_lines = rec.intervention_line_illisible_ids
            rec.total_illisible = sum(selected_lines.mapped('qte_illisible'))


    def calcul_total_ok(self):
        for rec in self:
            rec.total_ok = rec.pile_test + rec.test

    def calcul_total_hs(self):
        for rec in self:
            rec.total_hs = rec.code_erreur + rec.affichage_defectueux + rec.activation + rec.piles

    def calcul_total_cassee(self):
        for rec in self:
            rec.total_casse = rec.cassees + rec.esthetique


    def write(self, values):
        res = super(Carton, self).write(values)
    
        for rec in self:
            if rec.intervention_line_illisible_ids:
                for intervention_line in rec.intervention_line_illisible_ids:
                    existing_line_test = rec.env['intervention.line.eeg'].search([
                        ('illisible_id', '=', intervention_line.id),
                    ])
                    
                    if not existing_line_test:
                        line_values = {
                            'etiquette_id': intervention_line.etiquette_id.id,
                            'task_id': intervention_line.task_id.id,
                            'illisible': intervention_line.qte_illisible,
                            'carton_id': rec.id,
                            'illisible_id': intervention_line.id, 
                        }
                        rec.env['intervention.line.eeg'].create(line_values)
           
        return res
    pile_test = fields.Integer(string='Total Pile + Test', compute='calcul_total_pile_test')
    test = fields.Integer(string='Total test seulement', compute='calcul_total_test')
    code_erreur = fields.Integer(string='Total Code erreur', compute='calcul_total_code_erreur')
    affichage_defectueux = fields.Integer(string='Total ,Affichage défectueux', compute='calcul_total_affichage_defectueux')
    activation = fields.Integer(string='Total Activation', compute='calcul_total_activation')
    piles = fields.Integer(string='Total Piles', compute='calcul_total_piles')
    esthetique = fields.Integer(string='Total Esthétique', compute='calcul_total_esthetique')
    cassees = fields.Integer(string='Total Cassées', compute='calcul_total_ligne_cassee')

    @api.depends('intervention_line_eeg_ids.pile_test')
    def calcul_total_pile_test(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.pile_test = sum(selected_lines.mapped('pile_test'))

    @api.depends('intervention_line_eeg_ids.test')
    def calcul_total_test(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.test = sum(selected_lines.mapped('test'))

    @api.depends('intervention_line_eeg_ids.code_erreur')
    def calcul_total_code_erreur(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.code_erreur = sum(selected_lines.mapped('code_erreur'))

    @api.depends('intervention_line_eeg_ids.affichage_defectueux')
    def calcul_total_affichage_defectueux(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.affichage_defectueux = sum(selected_lines.mapped('affichage_defectueux'))


    @api.depends('intervention_line_eeg_ids.piles')
    def calcul_total_piles(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.piles = sum(selected_lines.mapped('piles'))

    @api.depends('intervention_line_eeg_ids.activation')
    def calcul_total_activation(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.activation = sum(selected_lines.mapped('activation'))

    @api.depends('intervention_line_eeg_ids.esthetique')
    def calcul_total_esthetique(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.esthetique = sum(selected_lines.mapped('esthetique'))

    @api.depends('intervention_line_eeg_ids.cassees')
    def calcul_total_ligne_cassee(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.cassees = sum(selected_lines.mapped('cassees'))



class InterventionLineEeg(models.Model):
    _name = 'intervention.line.eeg'
    _description = 'lines'

    # Define fields for the quotation
    etiquette_id = fields.Many2one('model.etiquette', 'Modèle')
    user_id = fields.Many2one(
        'res.users', string='Opened By',
        required=True,
        index=True,
        readonly=True,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    serial_number_10 = fields.Text(string='N° De série Base 10', compute='convert_base_10')
    serial_number_36 = fields.Text(string='N° de Série Base 36', copy=False)
    #_sql_constraints = [
     #       ('serial_number_36_unique', 'unique (serial_number_36)', 'Le N° de Série Base 36 doit être unique!'),
     #   ]
    task_id = fields.Many2one('project.task', 'Tâche', index=True, copy=False)

    carton_id = fields.Many2one('carton.carton', 'Carton')
    pile_test = fields.Integer('Pile + Test')
    test = fields.Integer('test seulement')
    code_erreur = fields.Integer('Code erreur')
    affichage_defectueux = fields.Integer('Affichage défectueux')
    activation = fields.Integer('Activation ')
    piles = fields.Integer('Piles')
    esthetique = fields.Integer('Esthétique')
    cassees = fields.Integer('Cassées')
    illisible = fields.Integer('Illisible')
    illisible_id = fields.Many2one('intervention.line.illisble', 'Illisible_id')
    quantity = fields.Float('Quantité OK')
    quantity_ok = fields.Integer(string='OK')
    quantity_hs = fields.Integer(string='HS')
    quantity_hs_piles = fields.Integer(string='HS Piles')
    quantity_illisible = fields.Integer(string='ILLISIBLE')
    quantity_cassees = fields.Integer(string='CASSEES')

    @api.depends('serial_number_36')
    def convert_base_10(self):
        for rec in self:
            if rec.serial_number_36 == False:
                rec.serial_number_10 = 0
            else:
                try:
                    rec.serial_number_10 = int(rec.serial_number_36, 36)
                except ValueError:
                    rec.serial_number_10 = 0 
                    #raise ValidationError(f"Le code-barres '{rec.serial_number_36}' n'est pas valide.")

    @api.model
    def create(self, values):
        if 'serial_number_36' in values:
            serial_number_36 = values.get('serial_number_36')   
            try:
                int(serial_number_36, 36)  # Tente de convertir le numéro de série
            except ValueError:
                raise ValidationError(f"Le code-barres '{serial_number_36}' n'est pas valide. L'importation a échoué.")
        return super(InterventionLineEeg, self).create(values)
        


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

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import timedelta
from odoo.exceptions import ValidationError,Warning

class inheritTask(models.Model):
    _inherit = 'project.task'

    qte_annoncee = fields.Integer(string='Qté annoncées')
    shipping_address = fields.Many2one('res.partner', string='Magasin', index=True, ondelete='cascade')
    qte_recue = fields.Integer(string='Qté reçues')
    qte_non_traitee = fields.Integer(string='Non Traité')
    carton_ids = fields.One2many('carton.carton', 'task_id', string='Cartons')
    cartons_count = fields.Integer(compute='_compute_cartons_count', string='Cartons Count')
    intervention_ids = fields.One2many('intervention.line.eeg', 'task_id', string='Lines')
    intervention_illisible_ids = fields.One2many('intervention.line.illisble', 'task_id', string='Lines Illisible')
    etiquette_count = fields.Integer(compute='_compute_intervention_count', string='Intervention Count')
    sequence1 = fields.Char(string='Dossier N°', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('project.tasksequence'))


    Total_illisible = fields.Integer(string='Total ILLISIBLES', compute='calcul_total_illisible')

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

    poids_carton = fields.Float(
        string="Poids",
        digits='Poids carton', default=0.0,
        store=True, readonly=False, required=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)



class MarqueEtiquette(models.Model):
    _name = 'marque.etiquette'
    _description = 'Marque Etiquette'

    name = fields.Text(string='Marque')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)


class ModelEtiquette(models.Model):
    _name = 'model.etiquette'
    _description ='Modèle Etiquette'

    # Define fields for the quotation
    name = fields.Text(string='Etiquette')
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True)
    marque_id = fields.Many2one('marque.etiquette', string='Marque', create=True)
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
    
    task_id = fields.Many2one('project.task','Tâche', default=lambda self: self._get_default_task(), index=True, copy=False)

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
    _sql_constraints = [
            ('serial_number_36_unique', 'unique (serial_number_36)', 'Le N° de Série Base 36 doit être unique!'),
        ]
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

    @api.depends('serial_number_36')
    def convert_base_10(self):
        for rec in self:
            if rec.serial_number_36 == False:
                rec.serial_number_10 = 0
            else:
                try:
                    rec.serial_number_10 = int(rec.serial_number_36, 36)
                except ValueError:
                    raise ValidationError("code-barres n'est pas valide")


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

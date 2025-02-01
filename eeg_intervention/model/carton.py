from odoo import api, fields, models, exceptions, SUPERUSER_ID, _


class ModelCarton(models.Model):
    _name = 'model.carton'
    _description = 'Modèle carton'

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
    active = fields.Boolean(string='Active', default=True)

    def action_archive(self):
        self.write({'active': False})

    def action_restore(self):
        self.write({'active': True})


class Carton(models.Model):
    _name = 'carton.carton'
    _description = 'Cartons'
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
    proprietaire_carton = fields.Selection([
        ('CLIENT', 'CLIENT'),
        ('ICR', 'ICR')
    ])
    task_id = fields.Many2one('project.task', 'Tâche', default=lambda self: self._get_default_task(), index=True,
                              copy=False)
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
    total_illisible = fields.Integer(string='Total Illisible', compute='calcul_total_illisibles')
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
    affichage_defectueux = fields.Integer(string='Total ,Affichage défectueux',
                                          compute='calcul_total_affichage_defectueux')
    activation = fields.Integer(string='Total Activation', compute='calcul_total_activation')
    piles = fields.Integer(string='Total Piles', compute='calcul_total_piles')
    esthetique = fields.Integer(string='Total Esthétique', compute='calcul_total_esthetique')
    cassees = fields.Integer(string='Total Cassées', compute='calcul_total_ligne_cassee')
    remplacement = fields.Integer(string='Etiquette de remplacement', compute='calcul_lignes_remplacee')
    reliquat_total = fields.Integer(string='Etiquette reliquat', compute='calcul_lignes_reliquat')

    @api.depends('intervention_line_eeg_ids.remplace')
    def calcul_lignes_remplacee(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.remplacement = sum(selected_lines.mapped('remplace'))

    @api.depends('intervention_line_eeg_ids.reliquat')
    def calcul_lignes_reliquat(self):
        for rec in self:
            selected_lines = rec.intervention_line_eeg_ids
            rec.reliquat_total = sum(selected_lines.mapped('reliquat'))

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

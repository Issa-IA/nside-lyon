from odoo import api, fields, models, exceptions, SUPERUSER_ID, _


class MarqueEtiquette(models.Model):
    _name = 'marque.etiquette'
    _description = 'Marque Etiquette'

    name = fields.Text(string='Marque')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Liste des prix')


class ModelEtiquette(models.Model):
    _name = 'model.etiquette'
    _description = 'Modèle Etiquette'

    # Define fields for the quotation
    name = fields.Text(string='Etiquette')
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True)
    marque_id = fields.Many2one('marque.etiquette', string='Marque', create=True)
    ref_eeg = fields.Char( string='Référence', store=True, index=True)
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
    serial_number_36 = fields.Text(string='N° de Série Base 36')
    task_id = fields.Many2one('project.task', 'Tâche', index=True, copy=False)
    active = fields.Boolean(string='Active' ,default=True,
                            store=True)


    def archive_record(self):
        for record in self:
            record.write({'active': False})

    carton_id = fields.Many2one('carton.carton', 'Carton')
    pile_test = fields.Integer('Pile + Test')
    test = fields.Integer('test seulement')
    code_erreur = fields.Integer('Code erreur')
    affichage_defectueux = fields.Integer('Affichage défectueux')
    activation = fields.Integer('Activation ')
    piles = fields.Integer('Piles')
    esthetique = fields.Integer('Esthétique')
    cassees = fields.Integer('Cassées')
    remplace = fields.Integer('Etiquette remplacé')
    reliquat = fields.Integer('Etiquette reliquat')
    illisible = fields.Integer('Illisible')
    illisible_id = fields.Many2one('intervention.line.illisble', 'Illisible_id')
    quantity = fields.Float('Quantité OK')
    quantity_ok = fields.Integer(string='OK')
    quantity_hs = fields.Integer(string='HS')
    quantity_hs_piles = fields.Integer(string='HS Piles')
    quantity_illisible = fields.Integer(string='ILLISIBLE')
    quantity_cassees = fields.Integer(string='CASSEES')
    quantity_remplacee = fields.Integer(string='REMPLACEE')

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
                    # raise ValidationError(f"Le code-barres '{rec.serial_number_36}' n'est pas valide.")


    @api.model
    def create(self, values):
        serial_number_36 = values.get('serial_number_36')

        # Vérifier si le numéro de série existe déjà
        # Vérifier si un enregistrement avec le même numéro de série existe déjà
        existing_record = self.search([('serial_number_36', '=', serial_number_36)], limit=1)

        # Si un enregistrement avec le même numéro de série existe déjà et n'est pas vide, afficher un message
        if existing_record and serial_number_36:
            raise exceptions.ValidationError(
                f"Le code-barres '{serial_number_36}' existe déjà. L'importation a échoué.")

        if serial_number_36:
            try:
                int(serial_number_36, 36)
            except ValueError:
                raise exceptions.ValidationError(
                    f"Le code-barres '{serial_number_36}' n'est pas valide. L'importation a échoué.")

        return super(InterventionLineEeg, self).create(values)

    related_archive_ids = fields.Many2many(
        comodel_name='project.task',
        string='Related Tasks',
        compute='_compute_related_archives',
        store=False,
    )

    def _compute_related_archives(self):
        ArchiveEeg = self.env['archive.eeg']

        for line in self:
            # Compare serial_number_10 as a string
            matching_archives = ArchiveEeg.search([('serial_number_10', '=', line.serial_number_10)])
            related_tasks = matching_archives.mapped('task_id')
            line.related_archive_ids = [(6, 0, related_tasks.ids)]


from odoo import api, fields, models, exceptions, SUPERUSER_ID, _
from dateutil.relativedelta import relativedelta
import qrcode
from io import BytesIO
import base64


class inheritTask(models.Model):
    _inherit = 'project.task'

    qte_annoncee = fields.Integer(string='Qté annoncées')
    shipping_address = fields.Many2one('res.partner', string='Magasin', index=True, ondelete='cascade')
    date_livraison = fields.Date(string='Date de Livraison')
    contact_store_id = fields.Many2one('res.partner', string='Contact du Magasin',
                                       domain="[('parent_id', '=', shipping_address)]")
    qte_recue = fields.Integer(string='Qté reçues')
    qte_non_traitee = fields.Integer(string='Non Traité')
    carton_ids = fields.One2many('carton.carton', 'task_id', string='Cartons')
    cartons_count = fields.Integer(compute='_compute_cartons_count', string='Cartons Count')
    intervention_ids = fields.One2many('intervention.line.eeg', 'task_id', string='Lines')
    intervention_illisible_ids = fields.One2many('intervention.line.illisble', 'task_id', string='Lines Illisible')
    etiquette_count = fields.Integer(compute='_compute_intervention_count', string='Intervention Count')
    sequence1 = fields.Char(string='Dossier N°', copy=False, readonly=True,
                            default=lambda self: self.env['ir.sequence'].next_by_code('project.tasksequence'))
    num_cartons_client = fields.Integer(string='Nombre de carton ICR', compute='_compute_num_cartons_client')
    pile_factured_total = fields.Float(string='Total Pile Facturée')
    remplacement_active = fields.Boolean(string='Remplacement', default=False, compute="update_remplacement")
    eeg_remplacee_ids = fields.One2many('eeg.remplacee', 'task_id', string='EEG Remplacee',
                                        compute="_compute_eeg_remplacee_ids", store=True)
    ecart = fields.Boolean(string='Écart', compute='_compute_ecart')

    count_reliquat = fields.Float(string='Total Reliquat', compute='_compute_count_reliquat', store=True)
    tag_ids = fields.Many2many('project.tags', string='Tags')
    image_ids = fields.One2many('task.image', 'task_id', string="Images")

    @api.depends('count_reliquat')
    def _update_tags_based_on_reliquat(self):
        partial_tag = self.env['project.tags'].browse(1)
        for task in self:
            if task.count_reliquat > 0:
                if partial_tag not in task.tag_ids:
                    task.tag_ids = [(4, partial_tag.id)]
            else:
                if partial_tag in task.tag_ids:
                    task.tag_ids = [(3, partial_tag.id)]

    @api.model
    def create(self, vals):
        task = super(inheritTask, self).create(vals)
        task._update_tags_based_on_reliquat()
        return task

    def write(self, vals):
        result = super(inheritTask, self).write(vals)
        self._update_tags_based_on_reliquat()
        return result

    @api.depends('intervention_ids.reliquat')
    def _compute_count_reliquat(self):
        for task in self:
            task.count_reliquat = sum(task.intervention_ids.mapped('reliquat'))

    @api.depends('qte_recue', 'qte_annoncee', 'name')
    def _compute_ecart(self):
        for record in self:
            if record.name and 'RFB' in record.name:
                record.ecart = record.qte_recue > record.qte_annoncee + 1000
            elif record.name and 'RMA' in record.name:
                if record.qte_annoncee != 0:
                    ecart_percent = (record.qte_recue - record.qte_annoncee) / record.qte_annoncee * 100
                    record.ecart = ecart_percent >= 10
                else:
                    record.ecart = False
            else:
                record.ecart = False

    date_reception = fields.Date(string='Date de réception', compute='_update_dates', store=True, inverse='_inverse_dates',)
    date_reception_client = fields.Date(string='Date de réception Client, compute='_update_dates', store=True, inverse='_inverse_dates',)
    date_expedition_tunisie = fields.Date(string='Date expédition en Tunisie', compute='_update_dates', store=True, inverse='_inverse_dates',)
    date_expedition_france = fields.Date(string='Date expédition en France', compute='_update_dates', store=True, inverse='_inverse_dates',)
    date_expedition = fields.Date(string='Date expédition', compute='_update_dates', store=True, inverse='_inverse_dates',)

    @api.depends('stage_id')
    def _update_dates(self):
        for rec in self:
            if self.stage_id.id == 98:
                new_date = fields.Date.today() + relativedelta(days=30)
                self.date_deadline = new_date.strftime('%Y-%m-%d')
                rec.date_reception = fields.Date.today().strftime('%Y-%m-%d')
            elif rec.stage_id.id == 149:
                today_date = fields.Date.today().strftime('%Y-%m-%d')
                rec.date_reception_client = today_date
            elif rec.stage_id.id == 125:
                rec.date_expedition_france = fields.Date.today().strftime('%Y-%m-%d')
            elif rec.stage_id.id == 148:
                rec.date_expedition = fields.Date.today().strftime('%Y-%m-%d')
    
    def _inverse_dates(self):
        # This method will store the editable fields' values
        pass


    @api.depends('eeg_remplacee_ids')
    def update_remplacement(self):
        for rec in self:
            if not rec.remplacement_active and any(eeg.quantity_remplacee != 0 for eeg in rec.eeg_remplacee_ids):
                rec.remplacement_active = True

    @api.depends('intervention_ids.remplace', 'intervention_ids.code_erreur', 'intervention_ids.affichage_defectueux',
                 'intervention_ids.activation', 'intervention_ids.piles')
    def _compute_eeg_remplacee_ids(self):
        for task in self:
            eeg_remplacee = task.intervention_ids.filtered(lambda line: line.etiquette_id and (
                        line.remplace or line.code_erreur or line.affichage_defectueux or line.activation or line.piles))

            quantity_dict = {}
            eeg_remplace_lines = self.env['intervention.line.eeg']
            for line in eeg_remplacee:
                etiquette_id = line.etiquette_id
                quantity_remplacee = line.remplace
                quantity_hs = line.code_erreur + line.affichage_defectueux + line.activation + line.piles

                if etiquette_id in quantity_dict:
                    quantity_dict[etiquette_id]['quantity_remplacee'] += quantity_remplacee
                    quantity_dict[etiquette_id]['quantity_hs'] += quantity_hs
                else:
                    quantity_dict[etiquette_id] = {
                        'quantity_remplacee': quantity_remplacee,
                        'quantity_hs': quantity_hs,
                    }
            for etiquette_id, quantities in quantity_dict.items():
                eeg_remplace_lines += self.env['intervention.line.eeg'].new({
                    'etiquette_id': etiquette_id.id,
                    'quantity_remplacee': quantities['quantity_remplacee'],
                    'quantity_hs': quantities['quantity_hs'],
                })

            task.eeg_remplacee_ids = [(5, 0, 0)] + [(0, 0, {
                'etiquette_id': line.etiquette_id.id,
                'quantity_remplacee': line.quantity_remplacee,
                'quantity_hs': line.quantity_hs,
            }) for line in eeg_remplace_lines]

    total_attente_remplacement = fields.Integer(string='Total En Attente de Remplacement',
                                                compute='_compute_total_attente_remplacement')

    @api.depends('eeg_remplacee_ids.attente_remplacement')
    def _compute_total_attente_remplacement(self):
        for task in self:
            task.total_attente_remplacement = sum(eeg.attente_remplacement for eeg in task.eeg_remplacee_ids)

    def action_view_total_attente_remplacement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'EEG Remplacee',
            'res_model': 'eeg.remplacee',
            'view_mode': 'list',
            'domain': [('task_id', '=', self.id)],
        }

    sale_order__intervention_id = fields.Many2one('sale.order', string='Commande intervention', store=True)

    @api.depends('carton_ids')
    def _compute_num_cartons_client(self):
        for task in self:
            num_cartons_client = len(task.carton_ids.filtered(lambda carton: carton.proprietaire_carton == 'ICR'))
            task.num_cartons_client = num_cartons_client

    Total_illisible = fields.Integer(string='Total ILLISIBLES', compute='calcul_total_illisible')
    transport_type = fields.Selection([('palette', 'Palette'), ('carton', 'Carton')], string='Transport',
                                      default='carton', readonly=False, compute='_compute_proprietaire_type')
    num_palette = fields.Integer(string='Quantité palette')

    @api.depends('cartons_count')
    def _compute_proprietaire_type(self):
        for record in self:
            if record.cartons_count > 7:
                record.transport_type = 'palette'
            else:
                record.transport_type = 'carton'

    piles_ids = fields.One2many('pile.model', 'task_id', string='Piles', compute='_compute_piles_ids', store=True)

    task_url = fields.Char(string="URL de la Tâche", compute="_compute_task_url")
    task_qr_code = fields.Html(string="QR Code de l'URL", compute="_compute_task_qr_code")

    @api.depends('name')
    def _compute_task_url(self):
        base_url_qr = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.task_url = "{}/web?#id={}&view_type=form&model=project.task".format(base_url_qr, record.id)

    @api.depends('task_url')
    def _compute_task_qr_code(self):
        for record in self:
            qr = qrcode.QRCode(
                version=1,  # Version du code QR (plus la version est élevée, plus le code est grand)
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,  # Taille des carrés du code QR (ajustez selon vos besoins)
                border=4,  # Taille de la bordure du code QR
            )
            qr.add_data(record.task_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img_byte_array = BytesIO()
            qr_img.save(qr_img_byte_array, format='PNG')
            qr_img_b64 = base64.b64encode(qr_img_byte_array.getvalue()).decode('utf-8')
            record.task_qr_code = '<img src="data:image/png;base64,%s"/>' % qr_img_b64

    @api.depends('intervention_ids.etiquette_id', 'intervention_ids.pile_test', 'intervention_ids.test',
                 'intervention_ids.affichage_defectueux', 'intervention_ids.code_erreur', 'intervention_ids.activation',
                 'intervention_ids.piles', 'intervention_ids.esthetique', 'intervention_ids.cassees',
                 'intervention_ids.illisible')
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

    @api.depends('intervention_ids.etiquette_id', 'intervention_ids.pile_test', 'intervention_ids.test',
                 'intervention_ids.affichage_defectueux', 'intervention_ids.code_erreur', 'intervention_ids.activation',
                 'intervention_ids.piles', 'intervention_ids.esthetique', 'intervention_ids.cassees',
                 'intervention_ids.illisible')
    def _compute_intervention_unique_ids(self):
        for task in self:
            unique_interventions = task.intervention_ids.filtered(
                lambda line: line.etiquette_id and (
                            line.pile_test or line.test or line.code_erreur or line.affichage_defectueux or line.activation or line.piles or line.esthetique or line.cassees or line.illisible))
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
                        'quantity_hs_piles': quantity_hs_piles,
                        'quantity_cassees': quantity_cassees,
                        'quantity_illisible': quantity_illisible,
                        'quantity': quantity
                    }

            unique_intervention_lines = self.env['intervention.line.eeg']

            for etiquette_id, quantities in quantity_dict.items():
                unique_intervention_lines += self.env['intervention.line.eeg'].new({
                    'etiquette_id': etiquette_id.id,
                    'quantity_ok': quantities['quantity_ok'],
                    'quantity_hs': quantities['quantity_hs'],
                    'quantity_hs_piles': quantities['quantity_hs_piles'],
                    'quantity_cassees': quantities['quantity_cassees'],
                    'quantity_illisible': quantities['quantity_illisible'],
                    'quantity': quantities['quantity'],
                })

            task.intervention_unique_ids = [(5, 0, 0)] + [
                (0, 0,
                 {'etiquette_id': line.etiquette_id.id, 'quantity_ok': line.quantity_ok, 'quantity': line.quantity,
                  'quantity_hs_piles': line.quantity_hs_piles, 'quantity_hs': line.quantity_hs,
                  'quantity_cassees': line.quantity_cassees, 'quantity_illisible': line.quantity_illisible}) for line in
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
            'context': {'search_default_task_id': self.id, 'default_task_id': self.id},
            'view_mode': 'tree,form',
        }

    def action_open_related_etiquettes(self):
        return {
            'name': 'EEG',
            'type': 'ir.actions.act_window',
            'res_model': 'intervention.line.eeg',
            'domain': [('task_id', '=', self.id)],
            'context': {'search_default_task_id': self.id, 'default_task_id': self.id},
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

    prestation_ids = fields.One2many('prestation.model', 'task_id', string='Prestations',
                                     compute='create_prestation_lines')
    intervention_unique_ids = fields.One2many('intervention.unique', 'task_id', string='Interventions Unique',
                                              compute='_compute_intervention_unique_ids', store=True)
    transport_product_carton = fields.Many2one('product.product', string='Transport product Carton', default=4252)
    transport_product_palette = fields.Many2one('product.product', string='Transport product palette', default=5711)
    product_carton = fields.Many2one('product.product', string='Product carton', default=5293)

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

    def traitement_admin(self):
        return {
            'name': 'Confirmation',
            'type': 'ir.actions.act_window',
            'res_model': 'confirmation.popup',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'task_id': self.id,
                'intervention_ids': self.intervention_ids.ids,
            },
        }

    def button_traitement_admin(self):
        self.traitement_admin()

        return {
            'type': 'ir.actions.act_window_close',
        }

    archives_ids = fields.One2many('archive.eeg', 'task_id', string='Archives Etiquettes')
    archive_eeg_count = fields.Integer(compute='_compute_archive_count', string='archive Count')

    def action_open_related_archives_ids(self):
        return {
            'name': 'Archives',
            'type': 'ir.actions.act_window',
            'res_model': 'archive.eeg',
            'domain': [('task_id', '=', self.id)],
            'context': {'search_default_task_id': self.id, 'default_task_id': self.id},
            'view_mode': 'tree,form',
        }

    @api.depends('archives_ids')
    def _compute_archive_count(self):
        for record in self:
            record.archive_eeg_count = len(record.archives_ids)

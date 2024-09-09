from odoo import api, fields, models, exceptions, SUPERUSER_ID, _

class ModelCarton(models.Model):
    _name = 'archive.eeg'
    _description = 'Archive étiquettes'

    name = fields.Text(string='Archive N°')
    carton_id = fields.Many2one('carton.carton', 'Carton')
    etiquette_id = fields.Many2one('model.etiquette', 'Modèle')
    ref_eeg = fields.Char(related='etiquette_id.ref_eeg', string='Référence EEG', store=True)
    task_id = fields.Many2one('project.task', 'Tâche', index=True, copy=False)
    serial_number_10 = fields.Text(string='N° De série Base 10')
    serial_number_36 = fields.Text(string='N° de Série Base 36')
    state_eeg = fields.Selection([
        ('BRK', 'BRK'),
        ('REP', 'REP'),
        ('SWA', 'SWA'),
        ('HS', 'HS')
    ])
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

class ConfirmationPopup(models.TransientModel):
    _name = 'confirmation.popup'
    _description = 'Confirmation Popup'

    confirm_delete = fields.Boolean(default=False)

    def action_confirm(self):
        task_id = self.env.context.get('task_id')
        intervention_ids = self.env.context.get('intervention_ids')

        if task_id and intervention_ids:
            task = self.env['project.task'].browse(task_id)
            interventions = self.env['intervention.line.eeg'].browse(intervention_ids)

            ArchiveEeg = self.env['archive.eeg']

            for intervention in interventions:
                if intervention.illisible or intervention.cassees or intervention.esthetique:
                    state = 'BRK'
                if intervention.pile_test:
                    state = 'REP'
                elif intervention.code_erreur or intervention.affichage_defectueux or intervention.activation or intervention.piles:
                    state = 'HS'
                elif intervention.remplace:
                    state = 'SWA'

                ArchiveEeg.create({
                    'name': 'Archive ' + str(intervention.id),
                    'carton_id': intervention.carton_id.id,
                    'etiquette_id': intervention.etiquette_id.id,
                    'task_id': task.id,
                    'ref_eeg': intervention.etiquette_id.ref_eeg,
                    'state_eeg': state,
                    'serial_number_10':  intervention.serial_number_10,
                    'serial_number_36':  intervention.serial_number_36,
                })


            if self.confirm_delete:
                interventions.unlink()

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

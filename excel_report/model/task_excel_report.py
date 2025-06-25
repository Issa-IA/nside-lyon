from odoo import api, fields, models, _
import io
import base64
from collections import defaultdict
from odoo.tools.misc import xlsxwriter


class TaskExcelReport(models.Model):
    _inherit = 'project.task'

    def model_task_excel_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('EEG Report')

        # Formats
        bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
        center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        yellow_fill = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        blue_fill = workbook.add_format({'bg_color': '#BDD7EE', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        green_fill = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1, 'align': 'center', 'valign': 'vcenter'})

        # Set column widths
        worksheet.set_column('A:D', 15)
        worksheet.set_column('E:ZZ', 8)

        # === EEG Models dynamiques (depuis etiquette_id.name) ===
        archives_all = self.env['archive.eeg'].search([('task_id', 'in', self.ids)])
        eeg_models = sorted(set(a.etiquette_id.name for a in archives_all if a.etiquette_id))

        retournee_start_col = 4
        retournee_model_cols = len(eeg_models) * 4
        total_cols = 5  # Totaux finaux
        retournee_end_col = retournee_start_col + retournee_model_cols + total_cols - 1

        # === En-têtes ===
        worksheet.merge_range('A1:A3', 'RMA PRESTATION', yellow_fill)
        worksheet.merge_range('B1:B3', "Date d'expedition", yellow_fill)
        worksheet.merge_range('C1:C3', 'TOTAL Traité', yellow_fill)
        worksheet.merge_range('D1:D3', 'total facturé', yellow_fill)

        # EEG RETOURNEE titre fusionné sur ligne 1
        worksheet.merge_range(0, retournee_start_col, 0, retournee_start_col + retournee_model_cols - 1, 'EEG RETOURNEE', blue_fill)

        # Ligne 2 : sous-titres pour EEG RETOURNEE par modèle (4 colonnes par modèle)
        col = retournee_start_col
        for model in eeg_models:
            worksheet.merge_range(1, col, 1, col + 3, model, green_fill)
            worksheet.write(2, col, 'REP', center)
            worksheet.write(2, col + 1, 'SWA', center)
            worksheet.write(2, col + 2, 'BRK', center)
            worksheet.write(2, col + 3, 'HS', center)
            col += 4

        # Totaux (fusion vertical sur les 3 lignes)
        total_start_col = retournee_start_col + retournee_model_cols
        total_labels = ['TOTAL BRK', 'TOTAL REP', 'TOTAL SWA', 'TOTAL HS', 'TOTAL EEG']
        for i, label in enumerate(total_labels):
            worksheet.merge_range(0, total_start_col + i, 2, total_start_col + i, label, yellow_fill)

        # === Préparation des données ===
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for archive in archives_all:
            task_id = archive.task_id.id
            model_name = archive.etiquette_id.name if archive.etiquette_id else None
            state = archive.state_eeg
            if task_id and model_name and state:
                data[task_id][model_name][state] += 1

        # === Remplissage du tableau ===
        row = 3
        for task in self:
            worksheet.write(row, 0, task.name or '', center)
            worksheet.write(row, 1, task.date_expedition.strftime('%d/%m/%Y') if getattr(task, 'date_expedition', False) else '', center)

            # TOTAL Traité = qte_recue - qte_non_traitee
            qte_recue = getattr(task, 'qte_recue', 0) or 0
            qte_non_traitee = getattr(task, 'qte_non_traitee', 0) or 0
            total_traite = qte_recue - qte_non_traitee
            worksheet.write(row, 2, total_traite, center)

            # total facturé
            total_facture = getattr(task, 'total_facture', 0) or 0
            worksheet.write(row, 3, total_facture, center)

            # EEG RETOURNEE par modèle
            col = retournee_start_col

            total_brk = 0
            total_rep = 0
            total_swa = 0
            total_hs = 0
            total_eeg = 0

            for model in eeg_models:
                rep = data[task.id][model].get('REP', 0)
                swa = data[task.id][model].get('SWA', 0)
                brk = data[task.id][model].get('BRK', 0)
                hs = data[task.id][model].get('HS', 0)

                worksheet.write(row, col, rep, center)
                worksheet.write(row, col + 1, swa, center)
                worksheet.write(row, col + 2, brk, center)
                worksheet.write(row, col + 3, hs, center)

                total_rep += rep
                total_swa += swa
                total_brk += brk
                total_hs += hs
                total_eeg += rep + swa + brk + hs

                col += 4

            # Totaux écrits directement (pas de formules Excel)
            worksheet.write(row, total_start_col + 0, total_brk, center)   # TOTAL BRK
            worksheet.write(row, total_start_col + 1, total_rep, center)   # TOTAL REP
            worksheet.write(row, total_start_col + 2, total_swa, center)   # TOTAL SWA
            worksheet.write(row, total_start_col + 3, total_hs, center)    # TOTAL HS
            worksheet.write(row, total_start_col + 4, total_eeg, center)   # TOTAL EEG

            row += 1

        # Finaliser le fichier
        workbook.close()
        output.seek(0)
        data_bytes = output.read()
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'Task_EEG_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(data_bytes),
            'res_model': self._name,
            'res_id': self.id if len(self) == 1 else False,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

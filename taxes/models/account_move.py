from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_aisi = fields.Boolean(string='AISI', default=False)

    def apply_aisi(self):
        # Recherche des taxes qui contiennent 'AISI' dans leur nom
        aisi_taxes = self.env['account.tax'].search([('name', 'ilike', 'AISI')])

        if not aisi_taxes:
            raise UserError('Aucune taxe contenant "AISI" dans son nom n\'a été trouvée.')

        # Utiliser sudo().exists() pour être sûr d'avoir des enregistrements valides
        # et filtrer les lignes qui ont product_id et tax_ids pour éviter les lignes vides
        valid_lines = self.sudo().line_ids.exists().filtered(
            lambda l: l.product_id and l.display_type not in ('line_section', 'line_note'))

        if self.is_aisi:
            # Traiter uniquement les lignes qui ont déjà des taxes
            tax_lines = valid_lines.filtered(lambda l: l.tax_ids)
            for line in tax_lines:
                try:
                    current_taxes = line.tax_ids
                    new_taxes = current_taxes | aisi_taxes
                    line.with_context(check_move_validity=False).tax_ids = new_taxes
                except Exception as e:
                    # Log l'erreur mais continue avec les autres lignes
                    print(f"Erreur lors de l'ajout de la taxe AISI à la ligne {line.id}: {str(e)}")
        else:
            # Compter combien de lignes contiennent des taxes AISI
            aisi_count = 0
            for line in valid_lines:
                try:
                    if line.tax_ids and any(tax.id in aisi_taxes.ids for tax in line.tax_ids):
                        aisi_count += 1
                        # Filtrer pour enlever les taxes AISI
                        filtered_taxes = line.tax_ids.filtered(lambda tax: tax.id not in aisi_taxes.ids)
                        line.with_context(check_move_validity=False).tax_ids = filtered_taxes
                except Exception as e:
                    # Log l'erreur mais continue avec les autres lignes
                    print(f"Erreur lors du retrait de la taxe AISI de la ligne {line.id}: {str(e)}")

            if aisi_count == 0:
                print('Aucune ligne ne contient de taxe AISI, rien à enlever.')


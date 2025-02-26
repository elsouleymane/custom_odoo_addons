from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_airsi = fields.Boolean(string='AIRSI', default=False)

    def apply_airsi(self):
        if self.move_type not in ['out_refund', 'in_refund']:
            raise UserError('La fonction AIRSI ne peut être appliquée que sur les avoirs.')

        airsi_taxes = self.env['account.tax'].search([('is_airsi', '=', True)])

        if not airsi_taxes:
            raise UserError('Aucune taxe avec le champ is_airsi n\'a été trouvée.')

        valid_lines = self.sudo().line_ids.exists().filtered(
            lambda l: l.product_id and l.display_type not in ('line_section', 'line_note'))

        if not valid_lines:
            return {'warning': {'title': 'Information',
                                'message': 'Aucune ligne valide trouvée pour appliquer les taxes AIRSI.'}}

        modified_count = 0

        if self.is_airsi:
            for line in valid_lines:
                try:
                    product = line.product_id
                    product_airsi_taxes = product.taxes_id.filtered(lambda t: t.is_airsi)

                    if product_airsi_taxes:
                        current_taxes = line.tax_ids
                        missing_airsi_taxes = product_airsi_taxes - current_taxes

                        if missing_airsi_taxes:
                            new_taxes = current_taxes | missing_airsi_taxes
                            line.with_context(check_move_validity=False).tax_ids = new_taxes
                            modified_count += 1
                except Exception as e:
                    _logger.error(f"Erreur lors de l'ajout de la taxe AIRSI à la ligne {line.id}: {str(e)}")
        else:
            for line in valid_lines:
                try:
                    if line.tax_ids and any(tax.id in airsi_taxes.ids for tax in line.tax_ids):
                        filtered_taxes = line.tax_ids.filtered(lambda tax: tax.id not in airsi_taxes.ids)
                        line.with_context(check_move_validity=False).tax_ids = filtered_taxes
                        modified_count += 1
                except Exception as e:
                    _logger.error(f"Erreur lors du retrait de la taxe AIRSI de la ligne {line.id}: {str(e)}")

        # Refresh the form view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'current'
        }
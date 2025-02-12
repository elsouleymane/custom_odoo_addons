from odoo import api, fields, models, _


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment"

    def _get_default_journal(self):
        return self.env['account.journal'].search([], limit=1)

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        default=_get_default_journal
    )

    def print_report(self):
        data = {}
        self.ensure_one()
        return self.env.ref('account.access_account_invoice_report').report_action(None, data=data)

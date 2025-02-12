# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    def _get_default_journal(self):
        return self.env['account.journal'].search([], limit=1)

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        default=_get_default_journal
    )

    def print_report(self):
        self.ensure_one()
        data = {}
        return self.env.ref('account.access_account_invoice_report').report_action(None, data=data)


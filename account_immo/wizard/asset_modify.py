# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare


class AssetModifyInherit(models.TransientModel):
    _inherit = "asset.modify"

    def sell_dispose(self):
        self.ensure_one()
        if self.gain_account_id == self.asset_id.account_depreciation_id or self.loss_account_id == self.asset_id.account_depreciation_id:
            raise UserError(_("You cannot select the same account as the Depreciation Account"))
        invoice_lines = self.env['account.move.line'] if self.modify_action == 'dispose' else self.invoice_line_ids
        return self.asset_id.set_to_close(invoice_line_ids=invoice_lines, date=self.date, message=self.name, invoice_ids=self.invoice_ids, loss_account_id=self.loss_account_id)


    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        if self.date <= self.asset_id.company_id._get_user_fiscal_lock_date():
            raise UserError(_("You can't re-evaluate the asset before the lock date."))

        old_values = {
            'method_number': self.asset_id.method_number,
            'method_period': self.asset_id.method_period,
            'value_residual': self.asset_id.value_residual,
            'salvage_value': self.asset_id.salvage_value,
        }

        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'value_residual': self.value_residual,
            'salvage_value': self.salvage_value,
        }
        if self.env.context.get('resume_after_pause'):
            date_before_pause = max(self.asset_id.depreciation_move_ids, key=lambda x: x.date).date if self.asset_id.depreciation_move_ids else self.asset_id.acquisition_date
            # We are removing one day to number days because we don't count the current day
            # i.e. If we pause and resume the same day, there isn't any gap whereas for depreciation
            # purpose it would count as one full day
            number_days = self.asset_id._get_delta_days(date_before_pause, self.date) - 1
            if float_compare(number_days, 0, precision_rounding=self.currency_id.rounding) < 0:
                raise UserError(_("You cannot resume at a date equal to or before the pause date"))

            asset_vals.update({'asset_paused_days': self.asset_id.asset_paused_days + number_days})
            asset_vals.update({'state': 'open'})
            self.asset_id.message_post(body=_("Asset unpaused. %s", self.name))

        current_asset_book = self.asset_id.value_residual + self.asset_id.salvage_value
        after_asset_book = self.value_residual + self.salvage_value
        increase = after_asset_book - current_asset_book

        new_residual = min(current_asset_book - min(self.salvage_value, self.asset_id.salvage_value), self.value_residual)
        new_salvage = min(current_asset_book - new_residual, self.salvage_value)
        residual_increase = max(0, self.value_residual - new_residual)
        salvage_increase = max(0, self.salvage_value - new_salvage)

        if not self.env.context.get('resume_after_pause'):
            self.asset_id._create_move_before_date(self.date, self.loss_account_id)

        # Check for residual/salvage increase while rounding with the company currency precision to prevent float precision issues.
        if self.currency_id.round(residual_increase + salvage_increase) > 0:
            move = self.env['account.move'].create({
                'journal_id': self.asset_id.journal_id.id,
                'date': fields.Date.today(),
                'move_type': 'entry',
                'line_ids': [
                    Command.create({
                        'account_id': self.account_asset_id.id,
                        'debit': residual_increase + salvage_increase,
                        'credit': 0,
                        'name': _('Value increase for: %(asset)s', asset=self.asset_id.name),
                    }),
                    Command.create({
                        'account_id': self.account_asset_counterpart_id.id,
                        'debit': 0,
                        'credit': residual_increase + salvage_increase,
                        'name': _('Value increase for: %(asset)s', asset=self.asset_id.name),
                    }),
                ],
            })
            move._post()
            asset_increase = self.env['account.asset'].create({
                'name': self.asset_id.name + ': ' + self.name if self.name else "",
                'currency_id': self.asset_id.currency_id.id,
                'company_id': self.asset_id.company_id.id,
                'method': self.asset_id.method,
                'method_number': self.method_number,
                'method_period': self.method_period,
                'method_progress_factor': self.asset_id.method_progress_factor,
                'acquisition_date': self.date + relativedelta(days=1),
                'value_residual': residual_increase,
                'salvage_value': salvage_increase,
                'prorata_date': self.date + relativedelta(days=1),
                'prorata_computation_type': 'daily_computation' if self.asset_id.prorata_computation_type == 'daily_computation' else 'constant_periods',
                'original_value': residual_increase + salvage_increase,
                'account_asset_id': self.account_asset_id.id,
                'account_depreciation_id': self.account_depreciation_id.id,
                'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                'journal_id': self.asset_id.journal_id.id,
                'parent_id': self.asset_id.id,
                'original_move_line_ids': [(6, 0, move.line_ids.filtered(lambda r: r.account_id == self.account_asset_id).ids)],
            })
            asset_increase.validate()

            subject = _('A gross increase has been created: ') + asset_increase._get_html_link()
            self.asset_id.message_post(body=subject)

        if increase < 0:
            if self.env['account.move'].search([('asset_id', '=', self.asset_id.id), ('state', '=', 'draft'), ('date', '<=', self.date)]):
                raise UserError(_('There are unposted depreciations prior to the selected operation date, please deal with them first.'))
            move = self.env['account.move'].create(self.env['account.move']._prepare_move_for_asset_depreciation({
                'amount': -increase,
                'asset_id': self.asset_id,
                'move_ref': _('Value decrease for: %(asset)s', asset=self.asset_id.name),
                'depreciation_beginning_date': self.date,
                'depreciation_end_date': self.date,
                'date': self.date,
                'asset_number_days': 0,
                'asset_value_change': True,
            }))._post()

        asset_vals.update({
            'value_residual': new_residual,
            'salvage_value': new_salvage,
        })
        self.asset_id.write(asset_vals)

        self.asset_id.compute_depreciation_board()

        self.asset_id.children_ids.write({
            'method_number': asset_vals['method_number'],
            'method_period': asset_vals['method_period'],
            'asset_paused_days': self.asset_id.asset_paused_days,
        })

        for child in self.asset_id.children_ids:
            child.compute_depreciation_board()
            child._check_depreciations()
            child.depreciation_move_ids.filtered(lambda move: move.state != 'posted')._post()
        tracked_fields = self.env['account.asset'].fields_get(old_values.keys())
        changes, tracking_value_ids = self.asset_id._mail_track(tracked_fields, old_values)
        if changes:
            self.asset_id.message_post(body=_('Depreciation board modified %s', self.name), tracking_value_ids=tracking_value_ids)
        self.asset_id._check_depreciations()
        self.asset_id.depreciation_move_ids.filtered(lambda move: move.state != 'posted')._post()
        return {'type': 'ir.actions.act_window_close'}

    @api.depends('asset_id', 'invoice_ids', 'invoice_line_ids', 'modify_action')
    def _compute_gain_or_loss(self):
        res = super(AssetModifyInherit, self)._compute_gain_or_loss()
        for record in self:
            if record.asset_id.state in ['cushioned','open']:
                record.gain_or_loss = 'loss'
        return res
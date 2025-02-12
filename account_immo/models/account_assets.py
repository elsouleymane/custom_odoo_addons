from datetime import datetime

from reportlab.platypus import SimpleDocTemplate

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from math import copysign
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_is_zero, formatLang, end_of
import psycopg2

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12

class AccountAssetInherit(models.Model):
    _inherit = "account.asset"

    code = fields.Char(string="Code")
    ref = fields.Char(string="Référence Technique")
    marque = fields.Char(string="Marque")
    #partner_id = fields.Many2one('res.partner', string="Fournisseur")
    partner_char = fields.Char(string="Fournisseur")
    invoice_number = fields.Char(string="Numéro de facture")
    invoice_date = fields.Date(string="Date de facture")
    immat = fields.Char(string="Immatriculation")
    seriial_number = fields.Char(string="Numéro de série")
    affectation = fields.Many2one('hr.department',string="Affectation")
    taux = fields.Float(string="Taux", compute="_compute_taux", store=True)
    plus_value = fields.Monetary(string="Plus value", compute="_compute_cession_value", store=True, readonly=False)
    moins_value = fields.Monetary(string="Moins value", compute="_compute_cession_value", store=True, readonly=False)
    cession_value = fields.Monetary(string="Valeur de la cession")
    book_value = fields.Monetary(string='Valeur comptable', readonly=False, compute='_compute_book_value', recursive=True,
                                 store=True,
                                 help="Sum of the depreciable value, the salvage value and the book value of all value increase items")
    value_residual = fields.Monetary(string='Valeur résiduelle', store=True, readonly=False)
    amort_total = fields.Monetary(string="Amortissemnent antérieur", compute="_compute_amort_total", store=True)
    cession_date = fields.Date(string="Date de cession")
    state = fields.Selection(
        selection=[('model', 'Modèle'),
                   ('draft', 'Brouillon'),
                   ('open', 'En cours'),
                   ('cushioned', 'Amorti'),
                   ('paused', 'En attente'),
                   ('close', 'Résilié'),
                   ('cancelled', 'Annulé')],
        string='Status',
        copy=False,
        default='draft',
        readonly=False,
        help="When an asset is created, the status is 'Draft'.\n"
             "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
             "The 'On Hold' status can be set manually when you want to pause the depreciation of an asset for some time.\n"
             "You can manually close an asset when the depreciation is over.\n"
             "By cancelling an asset, all depreciation entries will be reversed")

    journal_id = fields.Many2one(
        'account.journal',
        string="Journal d'amortissement",
        check_company=True,
        default=lambda self: self.env['account.journal'].search([('code','=','AMORT')]).id or False,
        domain="[('type', '=', 'general')]",
        compute='_compute_journal_id', store=True, readonly=False,
    )

    disposal_journal_id = fields.Many2one(
        'account.journal',
        string="Journal de cession",
        check_company=True,
        domain="[('type', '=', 'general')]",
        compute='_compute_journal_id',
        required=True, store=True, readonly=False,
    )

    invest = fields.Char(string="Financement bancaire")
    overtdate = fields.Date(string="Date Dern. Compt.")

    @api.depends('company_id')
    def _compute_journal_id(self):
        res = super(AccountAssetInherit,self)._compute_journal_id()
        for asset in self:
            if asset.disposal_journal_id and asset.disposal_journal_id.company_id == asset.company_id:
                asset.disposal_journal_id = asset.disposal_journal_id

            else:
                asset.disposal_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(asset.company_id),
                    ('type', '=', 'general'),
                ], limit=1)

        return res

    @api.onchange('account_asset_id')
    def compute_default_model_id(self):
        for rec in self:
            model = self.env['account.asset'].search([('state','=','model'),('account_asset_id','=',rec.account_asset_id.id)])
            if model:
                rec.model_id = model.id

            else:
                pass

    def calculate_total_asset(self):



    @api.constrains('code')
    def _check_code_unique(self):
        for rec in self:
            code_counts = self.search_count([('code', '=', rec.code)])
            if code_counts > 1:
                raise ValidationError("Le code %s existe dans la base!" % rec.code)

    @api.depends('state')
    def amort_action(self):
        for rec in self:
            rec.state = 'cushioned'

    @api.depends('value_residual','original_value')
    def _compute_amort_total(self):
         for rec in self:
            rec.amort_total = rec.original_value - rec.value_residual

    @api.depends('method_number')
    def _compute_taux(self):
        for rec in self:
            if rec.method_number == 0:
                rec.taux = 0
            else:
                rec.taux = 100 / rec.method_number


    def change_state(self):
        for rec in self:
            rec.state = 'open'

    def account_move(self):
        for rec in self:
            print('bbmmmmmmmm')

    def set_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft','cession_value': 0, 'plus_value': 0, 'moins_value': 0, 'amort_total': rec.already_depreciated_amount_import})

    @api.depends('cession_value')
    def _compute_cession_value(self):
        for rec in self:
            if rec.cession_value:
                gain_value = rec.cession_value - rec.value_residual

                if gain_value > 0:
                    rec.plus_value = gain_value
                    rec.moins_value = 0

                else:
                    rec.moins_value = abs(gain_value)
                    rec.plus_value = 0


    def set_to_close(self, invoice_line_ids, date=None, message=None, invoice_ids=None, loss_account_id=None):
        self.ensure_one()
        disposal_date = date or fields.Date.today()
        if disposal_date <= self.company_id._get_user_fiscal_lock_date():
            raise UserError(_("You cannot dispose of an asset before the lock date."))
        if invoice_line_ids and self.children_ids.filtered(lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(_("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))
        full_asset = self + self.children_ids
        move_ids = full_asset._get_disposal_moves([invoice_line_ids] * len(full_asset), disposal_date, invoice_ids, loss_account_id)
        for asset in full_asset:
            asset.message_post(body=
                _('Asset sold. %s', message if message else "")
                if invoice_line_ids else
                _('Asset disposed. %s', message if message else "")
            )
        full_asset.write({'state': 'close'})
        if move_ids:
            name = _('Disposal Move')
            view_mode = 'form'
            if len(move_ids) > 1:
                name = _('Disposal Moves')
                view_mode = 'tree,form'
            return {
                'name': name,
                'view_mode': view_mode,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': move_ids[0],
                'domain': [('id', 'in', move_ids)]
            }


    def _create_move_before_date(self, date,loss_account_id):
        """Cancel all the moves after the given date and replace them by a new one.

        The new depreciation/move is depreciating the residual value.
        """
        self._cancel_future_moves(date)
        all_lines_before_date = self.depreciation_move_ids.filtered(lambda x: x.date <= date)

        days_already_depreciated = sum(all_lines_before_date.mapped('asset_number_days'))
        days_left = self.asset_lifetime_days - days_already_depreciated
        days_to_add = sum([
            (mv.date - mv.asset_depreciation_beginning_date).days + 1 for mv in
            all_lines_before_date.filtered(lambda x: not x.reversed_entry_id and not x.reversal_move_id)
        ])

        imported_amount = self.already_depreciated_amount_import if not all_lines_before_date else 0
        value_residual = self.value_residual + self.already_depreciated_amount_import if not all_lines_before_date else self.value_residual

        beginning_depreciation_date = self.paused_prorata_date + relativedelta(days=days_to_add)

        days_depreciated, amount = self._compute_board_amount(value_residual, beginning_depreciation_date, date, days_already_depreciated, days_left, value_residual)


        if abs(imported_amount) <= abs(amount):
            amount -= imported_amount
        if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            posted_depreciation_moves = self.depreciation_move_ids.filtered(lambda mv: mv.state == 'posted')
            amount_depre = sum(posted_depreciation_moves.mapped('depreciation_value'))

            if posted_depreciation_moves:
                for asset in self:
                    partner = asset.original_move_line_ids.mapped('partner_id')
                    partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
                    analytic_distribution = asset.analytic_distribution
                    company_currency = asset.company_id.currency_id
                    current_currency = asset.currency_id
                    prec = company_currency.decimal_places
                    amount_currency = amount + amount_depre
                    amount = current_currency._convert(amount + amount_depre, company_currency, asset.company_id,
                                                       date)
                    move_line_1 = {
                        'name': asset.name,
                        'partner_id': partner.id,
                        'account_id': asset.account_depreciation_id.id,
                        'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                        'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                        'analytic_distribution': analytic_distribution,
                        'currency_id': current_currency.id,
                        'amount_currency': amount_currency,
                    }
                    move_line_2 = {
                        'name': asset.name,
                        'account_id': loss_account_id.id,
                        'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                        'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                        'analytic_distribution': analytic_distribution,
                        'currency_id': current_currency.id,
                        'amount_currency': -amount_currency,
                    }

                    move_vals = {
                        'partner_id': partner.id,
                        'date': date,
                        'journal_id': asset.disposal_journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                        'asset_id': asset.id,
                        'ref': _("%s: %s Comptabilisation d'amortissement", asset.name, asset.code),
                        #'asset_depreciation_beginning_date': beginning_depreciation_date,
                        #'asset_number_days': days_depreciated,
                        'name': '/',
                        # 'asset_value_change': vals.get('asset_value_change', False),
                        'move_type': 'entry',
                        'currency_id': current_currency.id,
                    }

                    AccountMove = self.env['account.move']
                    account_move = AccountMove.create(move_vals)
                    account_move._post()

            else:
                new_line = self._insert_depreciation_line(self.original_value - amount - self.already_depreciated_amount_import, beginning_depreciation_date, date, days_depreciated, loss_account_id)
                new_line._post()

            new_line_one = self._insert_depreciation_add_line(amount, beginning_depreciation_date, date,
                                                              loss_account_id)
            new_line_one._post()


            for asset in self:
                if imported_amount == 0:
                    asset.write(
                        {'book_value': value_residual, 'value_residual': value_residual})
                else:
                    if posted_depreciation_moves:
                        pass
                    else:
                        asset.write(
                            {'book_value': self.original_value - amount - self.already_depreciated_amount_import, 'value_residual': self.original_value - amount - self.already_depreciated_amount_import})

        if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
            new_line_one = self._insert_depreciation_add_line(amount,beginning_depreciation_date, date, loss_account_id)
            new_line_one._post()

            for asset in self:
                if imported_amount == 0:
                    asset.write(
                        {'book_value': 0, 'value_residual': 0})
                else:
                    asset.write(
                        {'book_value': 0, 'value_residual': 0})



    def _insert_depreciation_line(self, amount, beginning_depreciation_date, depreciation_date, days_depreciated, loss_account_id):
        """ Inserts a new line in the depreciation board, shifting the sequence of
        all the following lines from one unit.
        :param amount:          The depreciation amount of the new line.
        :param label:           The name to give to the new line.
        :param date:            The date to give to the new line.
        """
        self.ensure_one()
        AccountMove = self.env['account.move']

        for asset in self:
            partner = asset.original_move_line_ids.mapped('partner_id')
            partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
            analytic_distribution = asset.analytic_distribution
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            amount_currency = asset.original_value - amount if asset.already_depreciated_amount_import != 0 else asset.value_residual
            amount = current_currency._convert(amount_currency, company_currency, asset.company_id, depreciation_date)


            move_line_1 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': asset.account_depreciation_id.id,
                'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': amount_currency,
            }
            move_line_2 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': loss_account_id.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': -amount_currency,
            }

            move_vals = {
                'partner_id': partner.id,
                'date': depreciation_date,
                'journal_id': asset.disposal_journal_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                'asset_id': asset.id,
                'ref': _("%s: %s Comptabilisation d'amortissement", asset.name, asset.code),
                'asset_depreciation_beginning_date': beginning_depreciation_date,
                'asset_number_days': days_depreciated,
                'name': '/',
                # 'asset_value_change': vals.get('asset_value_change', False),
                'move_type': 'entry',
                'currency_id': current_currency.id,
            }

        return AccountMove.create(move_vals)

    def _insert_depreciation_add_line(self, amount,beginning_depreciation_date ,depreciation_date, loss_account_id):
        """ Inserts a new line in the depreciation board, shifting the sequence of
        """
        self.ensure_one()
        AccountMove = self.env['account.move']

        for asset in self:
            partner = asset.original_move_line_ids.mapped('partner_id')
            partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
            analytic_distribution = asset.analytic_distribution
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            amount_currency = asset.original_value
            amount = current_currency._convert(amount_currency, company_currency, asset.company_id, depreciation_date)
            posted_depreciation_moves = self.depreciation_move_ids.filtered(lambda mv: mv.state == 'posted')
            amount_depre = sum(posted_depreciation_moves.mapped('depreciation_value'))


            if asset.value_residual == 0 or asset.method_number == 0:
                amount = asset.original_value
                move_line_1 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_depreciation_id.id,
                    'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                    'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
                move_line_2 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': loss_account_id.id,
                    'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                    'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                    'analytic_distribution': analytic_distribution,
                    'currency_id': current_currency.id,
                    'amount_currency': -amount_currency,
                }

                move_vals = {
                    'partner_id': partner.id,
                    'date': depreciation_date,
                    'journal_id': asset.disposal_journal_id.id,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    'asset_id': asset.id,
                    'ref': _("%s: %s Comptabilisation d'amortissement", asset.name, asset.code),
                    'asset_depreciation_beginning_date': beginning_depreciation_date,
                    'name': '/',
                    # 'asset_value_change': vals.get('asset_value_change', False),
                    'move_type': 'entry',
                    'currency_id': current_currency.id,
                }

                account_move = AccountMove.create(move_vals)
                account_move._post()

            move_line_1 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': loss_account_id.id,
                'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': amount_currency,
            }
            move_line_2 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': asset.account_asset_id.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_distribution': analytic_distribution,
                'currency_id': current_currency.id,
                'amount_currency': -amount_currency,
            }

            move_vals = {
                'partner_id': partner.id,
                'date': depreciation_date,
                'journal_id': asset.disposal_journal_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                'asset_id': asset.id,
                'ref': _("%s : %s Sortie d'immobilisation", asset.name, asset.code),
                'asset_depreciation_beginning_date': beginning_depreciation_date,
                #'asset_number_days': vals['asset_number_days'],
                'name': '/',
                #'asset_value_change': vals.get('asset_value_change', False),
                'move_type': 'entry',
                'currency_id': current_currency.id,
            }

        return AccountMove.create(move_vals)

    @api.constrains('depreciation_move_ids')
    def _check_depreciations(self):
        pass
        # for asset in self:
        #     if (
        #             asset.state == 'open'
        #             and asset.depreciation_move_ids
        #             and not asset.currency_id.is_zero(
        #         asset.depreciation_move_ids.sorted(lambda x: (x.date, x.id))[-1].asset_remaining_value
        #     )
        #     ):
        #         raise UserError(_("The remaining value on the last depreciation line must be 0"))



    def _get_disposal_moves(self, invoice_lines_list, disposal_date, invoice_ids, loss_account_id):
        """Create the move for the disposal of an asset.

        :param invoice_lines_list: list of recordset of `account.move.line`
            Each element of the list corresponds to one record of `self`
            These lines are used to generate the disposal move
        :param disposal_date: the date of the disposal
        """
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'balance': -amount,
                'analytic_distribution': analytic_distribution,
                'currency_id': asset.currency_id.id,
                'amount_currency': -asset.company_id.currency_id._convert(
                    from_amount=amount,
                    to_currency=asset.currency_id,
                    company=asset.company_id,
                    date=disposal_date,
                )
            })

        move_ids = []
        assert len(self) == len(invoice_lines_list)

        for asset, invoice_line_ids in zip(self, invoice_lines_list):
            asset._create_move_before_date(disposal_date, loss_account_id)

            analytic_distribution = asset.analytic_distribution

            dict_invoice = {}
            invoice_amount = 0

            initial_amount = asset.original_value
            initial_account = asset.original_move_line_ids.account_id if len(asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id

            all_lines_before_disposal = asset.depreciation_move_ids.filtered(lambda x: x.date <= disposal_date)
            depreciated_amount = asset.currency_id.round(copysign(
                sum(all_lines_before_disposal.mapped('depreciation_value')) + asset.already_depreciated_amount_import,
                -initial_amount,
            ))
            depreciation_account = asset.account_depreciation_id
            for invoice_line in invoice_line_ids:
                dict_invoice[invoice_line.account_id] = copysign(invoice_line.balance, -initial_amount) + dict_invoice.get(invoice_line.account_id, 0)
                invoice_amount += copysign(invoice_line.balance, -initial_amount)

            list_accounts = [(amount, account) for account, amount in dict_invoice.items()]
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account)] + list_accounts + [(difference, difference_account)]
            posted_depreciation_moves = self.env['account.move'].search([('asset_id', '=', asset.id),('journal_id','=', asset.disposal_journal_id.id),('state','=','posted')])
            amount_depre = sum(posted_depreciation_moves.mapped('amount_total_signed'))
            amount_invoiceline = sum(invoice_line_ids.mapped('price_subtotal'))
            asset.write({'amort_total': amount_depre - asset.original_value, 'cession_date': disposal_date, 'cession_value': amount_invoiceline})
            move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids



    def _cancel_future_moves(self, date):
        """Cancel all the depreciation entries after the date given as parameter.

        When possible, it will reset those to draft before unlinking them, reverse them otherwise.

        :param date: date after which the moves are deleted/reversed
        """
        for asset in self:
            obsolete_moves = asset.depreciation_move_ids.filtered(lambda m: m.state == 'draft' or (
                not m.reversal_move_id
                and not m.reversed_entry_id
                and m.state == 'posted'
                and m.date > date
            ))
            obsolete_moves.unlink()



    def set_to_running(self):
        for rec in self:
            if rec.value_residual == 0 or rec.method_number == 0:
                rec.write({'state': 'open'})
            else:
                try:
                    if rec.depreciation_move_ids and not max(rec.depreciation_move_ids, key=lambda m: (m.date, m.id)).asset_remaining_value == 0:
                        rec.env['asset.modify'].create({'asset_id': rec.id, 'name': _('Reset to running')}).modify()
                    rec.write({'state': 'open'})
                except:
                    rec.write({'state': 'open'})




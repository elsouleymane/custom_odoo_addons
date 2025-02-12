from odoo import api, models
from datetime import datetime
from pytz import UTC


class AssetReport(models.AbstractModel):
    _name = 'report.gestion.report_asset_category_totals'
    _description = 'Asset Category Totals Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.asset'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.asset',
            'docs': docs,
            'data': data,
            'time': datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S'),
            'user': self.env.user,
        }


class AssetDepreciationReport(models.AbstractModel):
    _name = 'report.gestion.report_asset_depreciation'
    _description = 'Asset Depreciation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.asset'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.asset',
            'docs': docs,
            'data': data,
            'time': datetime.now(UTC).strftime('%Y-%m-%d%H:%M:%S'),'user': self.env.user,
        }

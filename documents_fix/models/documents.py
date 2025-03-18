from odoo import models
import base64
import io
import binascii

class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    def _get_is_multipage(self):
        if not self.datas or isinstance(self.datas, bool):
            return False

        try:
            stream = io.BytesIO(base64.b64decode(self.datas))
            # Rest of function will execute normally
            return super()._get_is_multipage()
        except (TypeError, binascii.Error):
            return False
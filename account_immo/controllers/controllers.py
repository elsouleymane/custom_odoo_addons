# -*- coding: utf-8 -*-
# from odoo import http


# class AccountImmo(http.Controller):
#     @http.route('/account_immo/account_immo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_immo/account_immo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_immo.listing', {
#             'root': '/account_immo/account_immo',
#             'objects': http.request.env['account_immo.account_immo'].search([]),
#         })

#     @http.route('/account_immo/account_immo/objects/<model("account_immo.account_immo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_immo.object', {
#             'object': obj
#         })


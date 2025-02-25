# -*- coding: utf-8 -*-
# from odoo import http


# class LocalAddons/taxes(http.Controller):
#     @http.route('/local_addons/taxes/local_addons/taxes', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/local_addons/taxes/local_addons/taxes/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('local_addons/taxes.listing', {
#             'root': '/local_addons/taxes/local_addons/taxes',
#             'objects': http.request.env['local_addons/taxes.local_addons/taxes'].search([]),
#         })

#     @http.route('/local_addons/taxes/local_addons/taxes/objects/<model("local_addons/taxes.local_addons/taxes"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('local_addons/taxes.object', {
#             'object': obj
#         })


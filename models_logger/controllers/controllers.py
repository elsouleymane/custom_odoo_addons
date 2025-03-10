# -*- coding: utf-8 -*-
# from odoo import http


# class ModelsLogger(http.Controller):
#     @http.route('/models_logger/models_logger', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/models_logger/models_logger/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('models_logger.listing', {
#             'root': '/models_logger/models_logger',
#             'objects': http.request.env['models_logger.models_logger'].search([]),
#         })

#     @http.route('/models_logger/models_logger/objects/<model("models_logger.models_logger"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('models_logger.object', {
#             'object': obj
#         })


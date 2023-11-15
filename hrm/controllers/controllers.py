# - * - coding: utf - 8 -
# *-
# from odoo import http
# from odoo.http import request

#
# class Hrm(http.Controller):
#     @http.route('/hrm/hrm/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"
#
#     @http.route('/hrm/hrm/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm.listing', {
#             'root': '/hrm/hrm',
#             'objects': http.request.env['hrm.hrm'].search([]),
#         })
#
#     @http.route('/hrm/hrm/objects/<model("hrm.hrm"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm.object', {
#             'object': obj
#         })

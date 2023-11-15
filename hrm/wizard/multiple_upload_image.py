from odoo import api, fields, models


class MultipleImage(models.TransientModel):
    _name = 'hrm.multi.image'
    _description = "Upload Multi Image"

    document_declaration = fields.Many2one('hrm.document_declaration')
    attachment_ids = fields.Many2many('ir.attachment', string='Upload hình ảnh')

    def action_save_images(self):
        current_active_document_dec = self.env['hrm.document_declaration'].sudo().browse(
            self.env.context.get('active_ids'))
        i = 0
        for img in self.attachment_ids:
            i += 1
            current_active_document_dec.write({
                "picture_ids": [(0, 0, {
                    'name': f'Hình ảnh-{i}',
                    'image': img.datas
                })]
            })

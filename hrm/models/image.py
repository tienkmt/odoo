from odoo import api, fields, models, tools, _


class HrmImage(models.Model):
    _name = 'hrm.image'
    _description = "Hình ảnh"
    _inherit = ['image.mixin']

    name = fields.Char(string="Tên")
    image = fields.Image(required=True)
    public_image_url = fields.Char(compute="_compute_public_image", stores=True)
    document_declaration = fields.Many2one('hrm.document_declaration')
    sequence = fields.Integer(default=10, index=True)

    @api.depends('image')
    def _compute_public_image(self):
        for rec in self:
            domain = [
                ('res_model', '=', rec._name),
                ('res_field', '=', 'image'),
                ('res_id', '=', rec.id),
            ]
            attachment_id = self.env['ir.attachment'].sudo().search(domain, limit=1)
            if not attachment_id.public:
                attachment_id.sudo().write({"public": True})

            rec.public_image_url = attachment_id.local_url

    def open_image(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.public_image_url,
            'target': 'new',
        }

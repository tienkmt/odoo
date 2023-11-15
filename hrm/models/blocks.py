import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from . import constraint


class Blocks(models.Model):
    _name = 'hrm.blocks'
    _description = 'Khối'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string='Tên khối', required=True, tracking=True)
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Hoạt Động', default=True)
    has_change = fields.Boolean(default=True)

    @api.constrains('name')
    def _check_name_case_insensitive(self):
        """ Kiểm tra trùng lặp dữ liệu không phân biệt hoa thường """
        for record in self:
            name = self.search([('id', '!=', record.id), ('active', 'in', (True, False))])
            for n in name:
                if n['name'].lower() == record.name.lower():
                    raise ValidationError(constraint.DUPLICATE_RECORD % 'Khối')

    @api.onchange('name', 'description')
    def _onchange_name(self):
        if not self.has_change:
            raise ValidationError("Bạn không có quyền chỉnh sửa bản ghi này.")

    def action_archive(self):
        """ Thực hiện kiểm tra điều kiện trước khi lưu trữ """
        for line in self:
            if not line.has_change:
                raise ValidationError(constraint.DO_NOT_ARCHIVE)
            else:
                # Tiến hành lưu trữ bản ghi
                return super(Blocks, self).action_archive()

    def unlink(self, context=None):
        """ Chặn không cho xoá khối 'Văn phòng' và 'Thương mại' """
        for line in self:
            if not line.has_change:
                raise ValidationError(constraint.DO_NOT_DELETE)
        return super(Blocks, self).unlink()

    @api.constrains("name")
    def _check_valid_name(self):
        """
        kiểm tra trường name không có ký tự đặc biệt.
        \W là các ký tự ko phải là chữ, dấu cách, _
        """
        for rec in self:
            if rec.name:
                if re.search(r"[\W]+", rec.name.replace(" ", "")) or "_" in rec.name:
                    raise ValidationError(constraint.ERROR_NAME % 'khối')

    # hàm này để hiển thị lịch sử lưu trữ
    def toggle_active(self):
        for record in self:
            record.active = not record.active
            if not record.active:
                record.message_post(body="Đã lưu trữ")
            else:
                record.message_post(body="Bỏ lưu trữ")

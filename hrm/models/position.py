import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessDenied
from . import constraint


class Position(models.Model):
    _name = 'hrm.position'
    _description = 'Vị trí'
    _rec_name = "work_position"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    work_position = fields.Char(string='Tên Vị Trí', required=True, tracking=True)
    block = fields.Selection(selection=[
        (constraint.BLOCK_OFFICE_NAME, constraint.BLOCK_OFFICE_NAME),
        (constraint.BLOCK_COMMERCE_NAME, constraint.BLOCK_COMMERCE_NAME)], string="Khối", required=True, tracking=True
        , default=lambda self: self.env.user.block_id)
    team_type = fields.Selection([('marketing', 'Marketing'), ('sale', 'Sale')], string='Loại đội ngũ',
                                 default='marketing')
    active = fields.Boolean(string='Hoạt Động', default=True)
    related = fields.Boolean(compute='_compute_related_field')
    check_blocks = fields.Char(default=lambda self: self.env.user.block_id)

    def _default_department(self):
        """" kiểm tra phòng ban mặc định của người dùng
            xây dựng danh sách phòng ban con và cháu"""
        if self.env.user.department_id:
            # xây dựng điều kiện tìm k
            func = self.env['hrm.utils']
            list_department = func.get_child_id(self.env.user.department_id, 'hrm_departments', 'superior_department')

            return [('id', 'in', list_department)]

    department = fields.Many2one("hrm.departments", string='Phòng/Ban', tracking=True, domain=_default_department)

    @api.onchange('block')
    def clear_form(self):
        if self.block == constraint.BLOCK_OFFICE_NAME:
            self.team_type = ''
        else:
            self.team_type = 'marketing'
    @api.constrains("work_position")
    def _check_valid_name(self):
        """
            kiểm tra trường name không có ký tự đặc biệt.
            \W là các ký tự ko phải là chữ, dấu cách _
        """
        for rec in self:
            if rec.work_position:
                if re.search(r"[\W]+", rec.work_position.replace(" ", "")) or "_" in rec.work_position:
                    raise ValidationError(constraint.ERROR_NAME % 'vị trí')

    @api.depends('block')
    def _compute_related_field(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị
        for record in self:
            record.related = record.block != constraint.BLOCK_OFFICE_NAME

    def toggle_active(self):
        """hàm này để hiển thị lịch sử lưu trữ"""
        for record in self:
            record.active = not record.active
            if not record.active:
                record.message_post(body="Đã lưu trữ")
            else:
                record.message_post(body="Bỏ lưu trữ")

    @api.constrains('work_position', 'block')
    def _check_name_block_combination(self):
        """ tên vị trí giống nhau nhưng khối khác nhau vẫn có thể lưu được
            Kiểm tra sự trùng lặp dựa trên kết hợp của work_position và block
        """
        for record in self:
            name = self.search([('id', '!=', record.id), ('active', 'in', (True, False))])
            for n in name:
                if n['work_position'].lower() == record.work_position.lower() and n.block == self.block:
                    raise ValidationError(constraint.DUPLICATE_RECORD % "Vị trí")

    @api.constrains('department')
    def check_access_right(self):
        func = self.env['hrm.utils']
        list_department = func.get_child_id(self.env.user.department_id, 'hrm_departments', 'superior_department')
        if self.env.user.block_id != 'full' and self.block != self.env.user.block_id:
            raise AccessDenied(f"Bạn không có quyền truy cập với khối {self.block}")
        elif self.department and list_department and self.department.id not in list_department:
            raise AccessDenied(f"Bạn không có quyền truy cập với phòng ban {self.department.name}")

    @api.constrains('work_position', 'block', 'active', 'department')
    def check_permission(self):
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME and self.block == constraint.BLOCK_COMMERCE_NAME:
            raise AccessDenied(f"Bạn không có quyền chỉnh sửa bản ghi này")
        elif self.env.user.block_id == constraint.BLOCK_COMMERCE_NAME and self.block == constraint.BLOCK_OFFICE_NAME:
            raise AccessDenied(f"Bạn không có quyền chỉnh sửa bản ghi này")

    @api.onchange('block')
    def clear_form(self):
        if self.block == constraint.BLOCK_OFFICE_NAME:
            self.team_type = ''
        else:
            self.team_type = 'marketing'

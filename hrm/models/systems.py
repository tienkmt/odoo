from odoo import models, api, fields
from odoo.exceptions import ValidationError, AccessDenied
from . import constraint
import re


class Systems(models.Model):
    _name = "hrm.systems"
    _description = "Hệ thống"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = "name"

    name = fields.Char(string="Tên hiển thị", compute="_compute_name", store=True, )
    name_system = fields.Char(string="Tên hệ thống", required=True, tracking=True)
    type_system = fields.Selection(constraint.TYPE_SYSTEM, string="Loại hệ thống", required=True, tracking=True)
    phone_number = fields.Char(string="Số điện thoại", tracking=True)
    chairperson = fields.Many2one('res.users', string="Chủ tịch")
    vice_president = fields.Many2one('res.users', string='Phó chủ tịch')
    active = fields.Boolean(string='Hoạt Động', default=True)
    company_ids = fields.One2many('hrm.companies', 'system_id', string='Công ty trong hệ thống')
    approval_id = fields.Many2one('hrm.approval.flow.object', tracking=True)
    res_user_id = fields.Many2one('res.users')

    def _default_systems(self):
        """Kiểm tra phòng ban mặc định của người dùng và xây dựng danh sách hệ thống con và cháu."""
        if self.env.user.system_id:
            func = self.env['hrm.utils']
            list_systems = func.get_child_id(self.env.user.system_id, 'hrm_systems', 'parent_system')
            return [('id', 'in', list_systems)]

    parent_system = fields.Many2one("hrm.systems", string='Hệ thống cha', tracking=True, domain=_default_systems)

    @api.depends("parent_system.name", "name_system")
    def _compute_name(self):
        """ Tính toán logic tên hiển thị """
        for rec in self:
            if rec.parent_system and rec.name_system:
                rec.name = f"{rec.parent_system.name}.{rec.name_system}"
            elif rec.name_system:
                rec.name = rec.name_system

    @api.constrains("chairperson", "vice_president")
    def _check_chairperson_and_vice_president(self):
        """ Kiểm tra xem chairperson và vice_president có trùng id không """
        for rec in self:
            chairperson_id = rec.chairperson.id if rec.chairperson else False
            vice_president_id = rec.vice_president.id if rec.vice_president else False

            if chairperson_id and vice_president_id and chairperson_id == vice_president_id:
                raise ValidationError("Chủ tịch và Phó chủ tịch không thể giống nhau.")

    @api.constrains("phone_number")
    def _check_phone_valid(self):
        """
        hàm kiểm tra số điện thoại: không âm, không có ký tự, có số 0 ở đầu
        """
        for rec in self:
            if rec.phone_number:
                if not re.match(r'^\d+$', rec.phone_number):
                    raise ValidationError("Số điện thoại không hợp lệ")

    @api.constrains('name', 'type_system')
    def _check_name_block_combination(self):
        """
            Tên vị trí giống nhau nhưng khối khác nhau vẫn có thể lưu được
            Kiểm tra sự trùng lặp dựa trên kết hợp của name và type_system
        """
        for record in self:
            name = self.search([('id', '!=', record.id), ('active', 'in', (True, False))])
            for n in name:
                if n['name'].lower() == record.name.lower() and n.type_system == self.type_system:
                    raise ValidationError(constraint.DUPLICATE_RECORD % "Hệ thống")

    # hàm này để hiển thị lịch sử lưu trữ
    def toggle_active(self):
        for record in self:
            record.active = not record.active
            if not record.active:
                record.message_post(body="Đã lưu trữ")
            else:
                record.message_post(body="Bỏ lưu trữ")

    @api.constrains('name', 'name_system', 'type_system', 'parent_system', 'active', 'phone_number', 'chairperson',
                    'vice_president')
    def check_access_create(self):
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            raise AccessDenied("Bạn không có quyền cấu hình một hệ thống nào.")

    # @api.depends("name_system")
    # def compute_list_parent(self, vals):
    #     sort_lst = []
    #     self._cr.execute(
    #         "SELECT LENGTH(name) - LENGTH(REPLACE(name, '.', '')) as count_dots, id FROM hrm_systems ORDER BY count_dots ASC")
    #     for item in self._cr.fetchall():
    #         sort_lst.append(self.env["hrm.systems"].browse(item[1]))
    #     return sort_lst

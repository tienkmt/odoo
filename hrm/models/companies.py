import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessDenied
from . import constraint


class Companies(models.Model):
    _name = "hrm.companies"
    _description = "Công ty"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Tên hiển thị", compute='_compute_name_company', store=True)
    name_company = fields.Char(string="Tên công ty", required=True, tracking=True)
    type_company = fields.Selection(selection=constraint.SELECT_TYPE_COMPANY, string="Loại hình công ty", required=True,
                                    tracking=True)
    phone_num = fields.Char(string="Số điện thoại", required=True, tracking=True)
    chairperson = fields.Many2one('res.users', string="Chủ hộ")
    vice_president = fields.Many2one('res.users', string='Phó hộ')
    approval_id = fields.Many2one('hrm.approval.flow.object', tracking=True)
    res_user_id = fields.Many2one('res.users')
    active = fields.Boolean(string='Hoạt Động', default=True)
    change_system_id = fields.Many2one('hrm.systems', string="Hệ thống", default=False)
    check_company = fields.Char(default=lambda self: self.env.user.company.ids)

    def _get_child_company(self):
        """ lấy tất cả công ty user được cấu hình trong thiết lập """
        list_child_company = []
        if self.env.user.company.ids:
            # nếu user đc cấu hình công ty thì lấy list id công ty con của công ty đó
            list_child_company = self.env['hrm.utils'].get_child_id(self.env.user.company, 'hrm_companies',
                                                                    "parent_company")
        elif not self.env.user.company.ids and self.env.user.system_id.ids:
            # nếu user chỉ đc cấu hình hệ thống
            # lấy list id công ty con của hệ thống đã chọn
            for sys in self.env.user.system_id:
                func = self.env['hrm.utils']
                list_child_company += func._system_have_child_company(sys.id)
        return list_child_company

    def _default_company(self):
        """ tạo bộ lọc các công ty user có thể cấu hình """
        if self.env.user.block_id != constraint.BLOCK_OFFICE_NAME and not self.env.user.company.ids and not self.env.user.system_id.ids:
            # nếu user không cấu hình công ty và hệ thống, khối khác văn phòng thì hiển thị all
            return []
        return [('id', 'in', self._get_child_company())]

    parent_company = fields.Many2one('hrm.companies', string="Công ty cha", tracking=True, domain=_default_company)

    def _default_system(self):
        """ tạo bộ lọc cho trường hệ thống user có thể cấu hình """
        if not self.env.user.company.ids and self.env.user.system_id.ids:
            temp = self.env['hrm.utils'].get_child_id(self.env.user.system_id, 'hrm_systems', "parent_system")
            list_systems = [t for t in temp]
            return [('id', 'in', list_systems)]
        if self.env.user.company.ids or self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            # nếu có công ty thì không hiển thị hệ thống
            return [('id', '=', 0)]
        return []

    system_id = fields.Many2one('hrm.systems', string="Hệ thống", required=True, tracking=True, domain=_default_system)

    @api.constrains('parent_company', 'system_id', 'type_company', 'phone_num', 'name_company', 'chairperson',
                    'vice_president')
    def _check_parent_company(self):
        """ kiểm tra xem user có quyền cấu hình công ty được chọn không """
        if self.env.user.company.id and self.parent_company.id and self.parent_company.id not in self._get_child_company():
            raise AccessDenied(f"Bạn không có quyền cấu hình công ty {self.parent_company.name}")
        elif self.env.user.system_id.ids:
            temp = self.env['hrm.utils'].get_child_id(self.env.user.system_id, 'hrm_systems', "parent_system")
            list_systems = [t for t in temp]
            # nếu user có cấu hình hệ thống thì kiểm tra xem hệ thống được chọn có thuộc hệ thống user đc cấu hình hay k
            # hoặc user không chọn công ty cha mà hệ thống vẫn chọn thì kiểm tra lại quyền cấu hình hệ thống
            if self.system_id.id not in list_systems or (not self.parent_company.id and self.env.user.company.ids):
                raise AccessDenied(f"Bạn không có quyền cấu hình hệ thống {self.system_id.name}")
        elif self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            raise AccessDenied("Bạn không có quyền cấu hình một hệ thống nào.")

    @api.depends('system_id.name', 'type_company', 'name_company')
    def _compute_name_company(self):
        """
        decorator này để tự động tạo Tên hiển thị theo logic 'Tiền tố . Tên hệ thông . Tên công ty'
        """
        for rec in self:
            name_main = rec.name_company or ''
            type_company = rec.type_company and rec.type_company[0].capitalize() or ''
            name_system = rec.system_id and rec.system_id.name or ''
            name_parts = [part for part in [type_company, name_system, name_main] if part]  # Lọc các trường không rỗng
            rec.name = '.'.join(name_parts)

    @api.onchange('parent_company')
    def _onchange_parent_company(self):
        """ decorator này  chọn cty cha
            sẽ tự hiển thị hệ thống mà công ty đó thuộc vào
        """
        company_system = self.parent_company.system_id
        if company_system:
            self.system_id = company_system
        elif self.change_system_id:
            self.system_id = self.change_system_id
        else:
            self.system_id = False

    @api.onchange('system_id')
    def _onchange_company(self):
        """decorator này  chọn lại hệ thống sẽ clear công ty cha"""
        self.change_system_id = self.system_id
        if not self.system_id.name:
            self.parent_company = False
        if self.system_id != self.parent_company.system_id:
            self.parent_company = False
            func = self.env['hrm.utils']
            list_systems_id = func._system_have_child_company(self.system_id.id)
            return {'domain': {'parent_company': [('id', 'in', list_systems_id)]}}

    @api.constrains("phone_num")
    def _check_phone_valid(self):
        """
        hàm kiểm tra số điện thoại: không âm, không có ký tự, có số 0 ở đầu
        """
        for rec in self:
            if rec.phone_num:
                if not re.match(r'^\d+$', rec.phone_num):
                    raise ValidationError(constraint.ERROR_PHONE)

    @api.constrains("chairperson", "vice_president")
    def _check_chairperson_and_vice_president(self):
        """ Kiểm tra xem chairperson và vice_president có trùng id không """
        for rec in self:
            chairperson_id = rec.chairperson.id if rec.chairperson else False
            vice_president_id = rec.vice_president.id if rec.vice_president else False

            if chairperson_id and vice_president_id and chairperson_id == vice_president_id:
                raise ValidationError("Chủ tịch và Phó chủ tịch không thể giống nhau.")

    # hàm này để hiển thị lịch sử lưu trữ
    def toggle_active(self):
        for record in self:
            record.active = not record.active
            if not record.active:
                record.message_post(body="Đã lưu trữ")
            else:
                record.message_post(body="Bỏ lưu trữ")

    @api.constrains('name', 'type_company')
    def _check_name_block_combination(self):
        # Kiểm tra sự trùng lặp dựa trên kết hợp của work_position và block
        for record in self:
            name = self.search([('id', '!=', record.id), ('active', 'in', (True, False))])
            for n in name:
                if n['name'].lower() == record.name.lower() and n.type_company == self.type_company:
                    raise ValidationError(constraint.DUPLICATE_RECORD % "Công ty")

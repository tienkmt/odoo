import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessDenied
from . import constraint



class DocumentListConfig(models.Model):
    _name = 'hrm.document.list.config'
    _description = 'Cấu hình danh sách tài liệu'

    name = fields.Char(string='Tên hiển thị', required=True)
    block_id = fields.Many2one('hrm.blocks', string='Khối', required=True, default=lambda self: self._default_block(),
                               tracking=True)
    check_blocks = fields.Char(default=lambda self: self.env.user.block_id)
    check_company = fields.Char(default=lambda self: self.env.user.company)
    document_list = fields.One2many('hrm.document.list', 'document_id', string='Danh sách tài liệu')
    related = fields.Boolean(compute='_compute_related_')
    see_record_with_config = fields.Boolean(default=True)

    update_confirm_document = fields.Selection(selection=constraint.UPDATE_CONFIRM_DOCUMENT, string="Cập nhật tài liệu")

    # các field lưu id của tài liệu tương ứng với cấu hình áp dụng cho HSNS
    new_config = fields.One2many('hrm.document.list', 'new_id')
    not_approved_and_new = fields.One2many('hrm.document.list', 'not_approved_and_new_id')
    all = fields.One2many('hrm.document.list', 'all_id')

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        self.env['hrm.utils']._see_record_with_config('hrm.document.list.config')
        return super(DocumentListConfig, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                               submenu=submenu)

    def get_child_company(self):
        list_child_company = []
        if self.env.user.company:
            list_child_company = self.env['hrm.utils'].get_child_id(self.env.user.company, 'hrm_companies',
                                                                    "parent_company")
        elif not self.env.user.company and self.env.user.system_id:
            func = self.env['hrm.utils']
            for sys in self.env.user.system_id:
                list_child_company += func._system_have_child_company(sys.id)
        return [('id', 'in', list_child_company)]

    company = fields.Many2one('hrm.companies', string="Công ty", tracking=True, domain=get_child_company)

    def _default_system(self):
        if not self.env.user.company.ids and self.env.user.system_id.ids:
            list_systems = self.env['hrm.utils'].get_child_id(self.env.user.system_id, 'hrm_systems', 'parent_system')
            return [('id', 'in', list_systems)]
        if self.env.user.company.ids and self.env.user.block_id == constraint.BLOCK_COMMERCE_NAME:
            return [('id', '=', 0)]
        return []

    system_id = fields.Many2one('hrm.systems', string="Hệ thống", tracking=True, domain=_default_system)

    def _default_department(self):
        if self.env.user.department_id:
            list_department = self.env['hrm.utils'].get_child_id(self.env.user.department_id,
                                                                 'hrm_departments', "superior_department")
            return [('id', 'in', list_department)]

    department_id = fields.Many2one('hrm.departments', string='Phòng ban', tracking=True, domain=_default_department)

    def _default_position_block(self):
        if self.env.user.block_id == constraint.BLOCK_COMMERCE_NAME and not self.department_id:
            position = self.env['hrm.position'].search([('block', '=', self.env.user.block_id)])
            return [('id', 'in', position.ids)]
        elif self.env.user.block_id == constraint.BLOCK_OFFICE_NAME and self.department_id:
            position = self.env['hrm.position'].search([('block', '=', self.env.user.block_id)])
            return [('id', 'in', position.ids)]
        else:
            return []

    position_id = fields.Many2one('hrm.position', string='Vị trí', domain=_default_position_block)

    def _default_block(self):
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            return self.env['hrm.blocks'].search([('name', '=', constraint.BLOCK_OFFICE_NAME)])
        else:
            return self.env['hrm.blocks'].search([('name', '=', constraint.BLOCK_COMMERCE_NAME)])

    @api.depends('block_id')
    def _compute_related_(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị
        for record in self:
            record.related = record.block_id.name == constraint.BLOCK_OFFICE_NAME

    @api.onchange('block_id')
    def _onchange_block(self):
        self.company = self.department_id = self.system_id = self.position_id = False
        if self.block_id:
            position = self.env['hrm.position'].search([('block', '=', self.block_id.name)])
            return {'domain': {'position_id': [('id', 'in', position.ids)]}}
        else:
            return {'domain': {'position_id': []}}

    @api.onchange('department_id')
    def _default_position(self):
        if self.department_id:
            position = self.env['hrm.position'].search([('department', '=', self.department_id.id)])
            return {'domain': {'position_id': [('id', 'in', position.ids)]}}

    @api.onchange('company')
    def _onchange_company(self):
        if not self.company:
            return
        self.system_id = self.company.system_id

    @api.onchange('system_id')
    def _onchange_system(self):
        if self.system_id != self.company.system_id:
            self.position_id = self.company = False
        if self.system_id:
            if not self.env.user.company:
                func = self.env['hrm.utils']
                list_id = func._system_have_child_company(self.system_id.id)
                return {'domain': {'company': [('id', 'in', list_id)]}}
            else:
                self.company = False
                return {'domain': {'company': self.get_child_company()}}

    @api.onchange('document_list')
    def set_sequence(self):
        i = 1
        for document in self.document_list:
            document.sequence = i
            i += 1

    @api.onchange('document_list')
    def _check_duplicate_document(self):
        list_document = [record.doc for record in self.document_list]
        seen = set()
        for item in list_document:
            if item in seen:
                raise ValidationError(f'Hồ sơ {item.name} đã có trong danh sách tài liệu')
            else:
                seen.add(item)

    @api.constrains('name', 'block_id', 'department_id', 'position_id', 'system_id', 'company')
    def check_duplicate_document_config(self):
        """hàm này để kiểm tra trùng lặp cấu hình danh sách tài liệu cho các đối tượng được áp dụng"""
        def check_exist_object(department_id=False, position_id=False, system_id=False, company=False):
            check = self.search([('block_id', '=', self.block_id.id), ('id', 'not in', [self.id, False]),
                                 ('department_id', '=', department_id), ('position_id', '=', position_id),
                                 ('system_id', '=', system_id), ('company', '=', company)])
            return check.ids

        if self.position_id and check_exist_object(position_id=self.position_id.id, department_id=self.department_id.id,
                                                   system_id=self.system_id.id, company=self.company.id):
            raise ValidationError(f"Đã có cấu hình danh sách tài liệu cho vị trí {self.position_id.work_position}")
        elif not self.position_id and self.department_id and check_exist_object(department_id=self.department_id.id):
            raise ValidationError(f"Đã có cấu hình danh sách tài liệu cho phòng ban {self.department_id.name}")
        elif self.company and check_exist_object(company=self.company.id, system_id=self.system_id.id):
            raise ValidationError(f"Đã có cấu hình danh sách tài liệu cho công ty {self.company.name}")
        elif not self.company and self.system_id and check_exist_object(system_id=self.system_id.id):
            raise ValidationError(f"Đã có cấu hình danh sách tài liệu cho hệ thống {self.system_id.name}")
        elif not self.system_id and not self.department_id and check_exist_object():
            raise ValidationError(f"Đã có cấu hình danh sách tài liệu cho khối {self.block_id.name}")

    def unlink(self):
        for record in self:
            document = self.env['hrm.employee.profile'].sudo().search([('document_config', '=', record.id)])
            if document:
                raise AccessDenied("Không thể xoá " + record.name)
        return super(DocumentListConfig, self).unlink()

    @api.constrains('name', 'block_id', 'system_id', 'department_id', 'company', 'document_list')
    def check_access_config_hrm(self):
        """Kiểm tra lại quyền khi lưu"""
        user = self.env.user
        # Khối đang cấu hình khác full và khác với khối trên bản ghi
        if user.block_id != 'full' and user.block_id != self.block_id.name:
            raise AccessDenied("Bạn không có quyền thao tác trên khối đang chọn!")
        else:
            # func là gọi từ hrm.utils để sử dụng lại hàm
            # Sử dụng get_child_id() là để lấy tất cả các phần tử là con của đối tượng được cấu hình
            func = self.env['hrm.utils']
            # Nếu người dùng được cấu hình công ty
            if self.env.user.company:
                list_child_company = func.get_child_id(self.env.user.company, 'hrm_companies', "parent_company")
                if self.company.id not in list_child_company:
                    raise AccessDenied("Bạn không có quyền thao tác hoặc công ty đang chọn chưa cấu hình quyền cho bạn!")
            # Nếu người dùng được cấu hình hệ thống (không có cấu hình công ty)
            if self.env.user.system_id and not self.env.user.company:
                list_child_system = self.env['hrm.utils'].get_child_id(self.env.user.system_id, 'hrm_systems',
                                                                       "parent_system")
                if self.system_id.id not in list_child_system:
                    raise AccessDenied(
                        "Bạn không có quyền thao tác hoặc hệ thống đang chọn chưa cấu hình quyền cho bạn!")
            # Nếu người dùng được cấu hình phòng ban
            if self.env.user.department_id:
                list_department = func.get_child_id(self.env.user.department_id, 'hrm_departments',
                                                    'superior_department')
                if self.department_id and self.department_id.id not in list_department:
                    raise AccessDenied(
                        "Bạn không có quyền thao tác hoặc phòng ban đang chọn chưa cấu hình quyền cho bạn!")

    @api.constrains('document_list')
    def check_approval_flow_link(self):
        """Kiểm tra xem danh sách tài liệu có phần tử nào chưa, và ít nhất phải có 1 tài liệu tích bắt buộc"""
        if not self.document_list:
            raise ValidationError('Không thể tạo khi không có tài liệu nào trong danh sách tài liệu.')
        else:
            list_check = []
            for item in self.document_list:
                if item.obligatory:
                    list_check.append(True)
            if not any(list_check):
                raise ValidationError('Cần có ít nhất một tài liệu bắt buộc.')

    def action_update_document(self, object_update):
        # self.sudo().write({'update_confirm_document': object_update})
        if object_update == 'all':
            self.env['hrm.employee.profile'].sudo().search([('document_config', '=', self.id)]).write(
                {'type_update_document': 'all'}
            )
            self.all = [(6, 0, self.document_list.ids)]
        elif object_update == 'not_approved_and_new':
            self.env['hrm.employee.profile'].sudo().search([
                ('document_config', '=', self.id),
                ('state', 'in', ('draft','pending'))
            ]).write(
                {'type_update_document': 'not_approved_and_new'}
            )
            self.not_approved_and_new = [(6, 0, self.document_list.ids)]
        else:
            self.env['hrm.employee.profile'].sudo().search([
                ('document_config', '=', self.id),
                ('state', '=', 'draft')
            ]).write(
                {'type_update_document': 'new'}
            )
            self.new_config = [(6, 0, self.document_list.ids)]

class DocumentList(models.Model):
    _name = 'hrm.document.list'
    _description = 'Danh sách tài liệu'

    document_id = fields.Many2one('hrm.document.list.config')
    new_id = fields.Many2one('hrm.document.list.config')
    not_approved_and_new_id = fields.Many2one('hrm.document.list.config')
    all_id = fields.Many2one('hrm.document.list.config')
    sequence = fields.Integer(string="STT")
    doc = fields.Many2one('hrm.documents', string='Tên tài liệu')
    name = fields.Char(related='doc.name')
    obligatory = fields.Boolean(string='Bắt buộc')

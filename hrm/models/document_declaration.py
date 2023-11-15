from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from . import constraint


class DocumentDeclaration(models.Model):
    _name = 'hrm.document_declaration'
    _description = 'Khai báo tài liệu'

    name = fields.Char(string='Tên hiển thị', compute='_compute_name_team', store=True)
    profile_id = fields.Many2one('hrm.employee.profile')
    type_documents = fields.Many2one('hrm.documents', string='Loại tài liệu', required=True)
    block_id = fields.Many2one('hrm.blocks', string='Khối', required=True, related='employee_id.block_id')
    related = fields.Boolean(compute='_compute_related_')
    employee_id = fields.Many2one('hrm.employee.profile', string='Nhân viên', required=True)
    system_id = fields.Many2one('hrm.systems', string='Hệ thống', related='employee_id.system_id')
    company = fields.Many2one('hrm.companies', string='Công ty', related='employee_id.company')
    department_id = fields.Many2one('hrm.departments', string='Phòng ban', related='employee_id.department_id')
    give_back = fields.Boolean(string='Trả lại khi chấm dứt')
    manager_document = fields.Many2one('res.users', string='Quản lý tài liệu')
    complete = fields.Boolean(string='Hoàn thành')

    attachment_ids = fields.Many2many('ir.attachment', 'model_attachment_rel', 'model_id', 'attachment_id',
                                      string='Tệp tài liệu')

    picture_ids = fields.One2many('hrm.image', 'document_declaration', string="Hình ảnh")
    document_public_image_url = fields.Char(compute='_compute_image_related_fields', compute_sudo=True, store=True)
    see_record_with_config = fields.Boolean(default=True)
    max_photos = fields.Char(related='type_documents.numbers_of_photos')
    max_files = fields.Char(related='type_documents.numbers_of_documents')

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        self.env['hrm.utils']._see_record_with_config('hrm.document_declaration')
        return super(DocumentDeclaration, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                submenu=submenu)

    @api.depends('employee_id', 'type_documents')
    def _compute_name_team(self):
        """
        Phần này tự động tạo tên hiển thị dựa trên logic 'Tên nhân viên _ Loại tài liệu'.
        """
        for rec in self:
            employee_name = rec.employee_id.name if rec.employee_id else ''
            type_name = rec.type_documents.name if rec.type_documents else ''

            if employee_name and type_name:
                rec.name = f"{employee_name}_{type_name}"
            else:
                rec.name = ''

    @api.constrains('attachment_ids', 'picture_ids')
    def check_attchachment_count(self):
        if int(self.max_files) == 0:
            return
        if len(self.attachment_ids) > int(self.max_files):
            raise ValidationError(_(f"Số lượng tài liệu tải lên giới hạn là {self.max_files}"))

        if int(self.max_photos) == 0:
            return
        if len(self.picture_ids) > int(self.max_photos):
            raise ValidationError(_(f"Số lượng ảnh tải lên giới hạn là {self.max_photos}"))

    @api.depends('block_id')
    def _compute_related_(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị
        for record in self:
            record.related = record.block_id.name == constraint.BLOCK_OFFICE_NAME

    @api.onchange('name')
    def default_employee(self):
        """Gán giá trị của trường nhân viên khi tạo mới bản ghi tại màn Tạo mới hồ sơ."""
        if self.profile_id:
            self.employee_id = self.profile_id.id

    @api.onchange('employee_id')
    def domain_type_documents(self):
        if self.employee_id:
            domain = []
            for line in self.employee_id.document_config.document_list:
                domain.append(line.doc.id)
            return {'domain': {'type_documents': [('id', 'in', domain)]}}
        return {'domain': {'type_documents': [('id', '=', 0)]}}

    @api.constrains('employee_id')
    def default_profile_id(self):
        """Dùng để khi tạo mới ở khai báo tài liệu, link luôn sang màn HSNS"""
        if self.employee_id:
            self.profile_id = self.employee_id.id

    @api.depends("picture_ids", "picture_ids.public_image_url")
    def _compute_image_related_fields(self):
        for rec in self:
            if rec.picture_ids and len(rec.picture_ids) > 0:
                rec.document_public_image_url = ",".join(rec.picture_ids.mapped('public_image_url'))

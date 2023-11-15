from odoo import models, fields, api
from . import constraint
from odoo.exceptions import ValidationError, AccessDenied


class Approval_flow_object(models.Model):
    _name = "hrm.approval.flow.object"
    _description = "Luồng phê duyệt"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string='Tên luồng phê duyệt', required=True, tracking=True)
    block_id = fields.Many2one('hrm.blocks', string='Khối', required=True, tracking=True
                               , default=lambda self: self.env['hrm.utils'].default_block_())
    check_blocks = fields.Char(default=lambda self: self.env.user.block_id)
    check_company = fields.Char(default=lambda self: self.env.user.company)
    approval_flow_link = fields.One2many('hrm.approval.flow', 'approval_id', tracking=True)
    related = fields.Boolean(compute='_compute_related_')

    def get_child_company(self):
        """ lấy tất cả công ty user được cấu hình trong thiết lập """
        list_child_company = []
        if self.env.user.company:
            # nếu user đc cấu hình công ty thì lấy list id công ty con của công ty đó
            list_child_company = self.env['hrm.utils'].get_child_id(self.env.user.company, 'hrm_companies',
                                                                    "parent_company")
        elif not self.env.user.company and self.env.user.system_id:
            # nếu user chỉ đc cấu hình hệ thống
            # lấy list id công ty con của hệ thống đã chọn
            func = self.env['hrm.utils']
            for sys in self.env.user.system_id:
                list_child_company += func._system_have_child_company(sys.id)
        elif self.env.user.block_id in ['full', constraint.BLOCK_COMMERCE_NAME]:
            return list_child_company
        return [('id', 'in', list_child_company)]

    company = fields.Many2many('hrm.companies', string="Công ty con", tracking=True, domain=get_child_company)

    def _default_departments(self):
        """Hàm này để hiển thị ra các phòng ban mà tài khoản có thể làm việc"""
        if self.env.user.department_id:
            func = self.env['hrm.utils']
            list_department = func.get_child_id(self.env.user.department_id, 'hrm_departments',
                                                'superior_department')
            return [('id', 'in', list_department)]

    department_id = fields.Many2many('hrm.departments', string='Phòng/Ban', tracking=True, domain=_default_departments)

    def _default_system(self):
        """ tạo bộ lọc cho trường hệ thống user có thể cấu hình """
        if self.env.user.system_id.ids:
            list_systems = self.env['hrm.utils'].get_child_id(self.env.user.system_id, 'hrm_systems', "parent_system")
            return [('id', 'in', list_systems)]
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            # nếu khối là văn phòng thì không hiển thị hệ thống
            return [('id', '=', 0)]
        return []

    system_id = fields.Many2many('hrm.systems', string="Hệ thống", tracking=True, store=True, domain=_default_system)

    @api.onchange('approval_flow_link')
    def _check_duplicate_approval(self):
        """decorator này để check trùng nhân viên tham gia luồng phê duyệt"""
        list_user_approve = [record.approve for record in self.approval_flow_link]
        seen = set()
        for item in list_user_approve:
            if item in seen:
                raise ValidationError(f'Người dùng tên {item.name} đã có trong luồng duyệt')
            else:
                seen.add(item)

    @api.constrains('approval_flow_link')
    def check_approval_flow_link(self):
        for record in self:
            if not record.approval_flow_link:
                raise ValidationError('Không thể tạo luồng phê duyệt khi không có người phê duyệt trong luồng.')
            else:
                list_check = []
                for item in record.approval_flow_link:
                    if item.obligatory:
                        list_check.append(True)
                if not any(list_check):
                    raise ValidationError('Luồng phê duyệt cần có ít nhất một người bắt buộc phê duyệt.')

    @api.depends('block_id')
    def _compute_related_(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị
        for record in self:
            record.related = record.block_id.name == constraint.BLOCK_OFFICE_NAME

    @api.constrains("block_id", "department_id", "system_id", "company")
    def _check_duplicate_config_office(self):
        """ Kiểm tra trùng lặp cấu hình """

        def get_list_configured(data):
            """ Trả về danh sách id các đối tượng được cấu hình trong danh sách tất cả id """
            return [i.id for d in data if d for i in d]

        def check_duplicate_for_object(objects, field_name):
            """ kiểm tra trùng lặp cấu hình cho một đối tượng """
            configured_objects = [rec[field_name] for rec in
                                  self.env["hrm.approval.flow.object"].search([("id", "!=", self.id)])]
            for obj in objects:
                if obj.id in get_list_configured(configured_objects):
                    raise ValidationError(f"Luồng phê duyệt cho {obj.name} đã tồn tại.")

        def system_have_child_company(system_id):
            """
            Kiểm tra hệ thống có công ty con hay không
            Nếu có thì trả về list tên công ty con
            """
            self._cr.execute(
                r"""
                    select hrm_companies.id from hrm_companies where hrm_companies.system_id in 
                        (WITH RECURSIVE subordinates AS (
                        SELECT id, parent_system
                        FROM hrm_systems
                        WHERE id = %s
                        UNION ALL
                        SELECT t.id, t.parent_system
                        FROM hrm_systems t
                        INNER JOIN subordinates s ON t.parent_system = s.id
                        )
                SELECT id FROM subordinates);
                """, (system_id,)
            )
            # kiểm tra company con của hệ thống cần tìm
            # nếu câu lệnh có kết quả trả về thì có nghĩa là hệ thống có công ty con
            list_company = self._cr.fetchall()
            if len(list_company) > 0:
                return [com[0] for com in list_company]
            return []

        if self.department_id:
            # Nếu có chọn cấu hình phòng ban thì chỉ cần check theo phòng ban
            check_duplicate_for_object(self.department_id, "department_id")
            return
        elif self.company:
            # Nếu có chọn cấu hình công ty thì chỉ cần check theo công ty
            check_duplicate_for_object(self.company, "company")
        if self.system_id:
            # Hệ thống không có công ty con thì mới đc cấu hình
            for system in self.system_id:
                # nếu hệ thống đã chọn không có công ty con trong công ty đã chọn thì mới tiếp tục kiểm tra
                if not any(com in system_have_child_company(system.id) for com in self.company.ids):
                    # tìm các cấu hình hệ thống đã có trong hệ thống được chọn
                    record_temp_configured = [(rec["name"], rec["system_id"], rec["company"]) for rec in
                                              self.env["hrm.approval.flow.object"].search(
                                                  [("id", "!=", self.id), ("system_id", "=", system.id)])]
                    # record[0]: tên luồng cấu hình
                    # record[1]: hệ thống được cấu hình
                    # record[2]: công ty được cấu hình
                    for record in record_temp_configured:
                        for sys in record[1]:
                            # nếu hệ thống không có công ty con trong các bản ghi khác là đã cấu hình
                            if sys.id == system.id and not any(
                                    com in system_have_child_company(sys.id) for com in record[2].ids):
                                raise ValidationError(
                                    f"Luồng phê duyệt cho {sys.name} đã tồn tại trong cấu hình {record[0]}.")
        elif self.block_id:
            # Kiểm tra bản ghi cấu hình cho khối văn phòng hoặc thương mại đã được cấu hình hay chưa
            # nếu có thì block_configured sẽ có kết quả sau đó raise thông báo
            block_configured = self.env["hrm.approval.flow.object"].search([
                ("id", "!=", self.id),
                ("block_id", "=", self.block_id.id),
                ("department_id", "=", False),
                ("company", "=", False),
                ("system_id", "=", False)
            ])
            if block_configured:
                raise ValidationError(
                    f"Luồng phê duyệt cho {self.block_id.name} đã tồn tại trong {block_configured[0].name}.")

    @api.onchange('block_id')
    def _onchange_block(self):
        self.company = self.department_id = self.system_id = False

    @api.onchange('system_id')
    def _onchange_system_id(self):
        """
            Decorator này khi chọn 1 hệ thống nào đó sẽ hiện ra tất cả những cty có trong hệ thống đó
            Xoá bỏ công ty nếu trong trường hệ thống không có hệ thống công ty đó thuộc
        """
        if self.system_id:
            # khi bỏ trường hệ thống thì loại bỏ các cty con của nó
            current_company_ids = self.company.ids
            child_company = []
            func = self.env['hrm.utils']
            for sys in self.system_id:
                child_company += func._system_have_child_company(sys.id.origin)
            # lấy ra cty chung trong hai list cty
            company_ids = list(set(current_company_ids) & set(child_company))
            self.company = [(6, 0, company_ids)]
            # lấy domain cho trường công ty
            if not self.env.user.company:
                list_id = []
                fun = self.env['hrm.utils']
                for sys_id in self.system_id.ids:
                    list_id += func._system_have_child_company(sys_id)
                return {'domain': {'company': [('id', 'in', list_id)]}}
            else:
                return {'domain': {'company': [('id', 'in', self.get_child_company())]}}
        self.company = [(6, 0, [])]

    @api.constrains('name', 'block_id', 'system_id', 'company', 'department_id')
    def check_permission(self):
        """ kiểm tra xem user có quyền cấu hình khối, hệ thống, cty, văn phòng hay không"""
        func = self.env['hrm.utils']
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            # nếu là khối văn phòng
            if self.env.user.department_id.ids:
                # nếu user có cấu hình phòng ban thì kiểm tra xem các phòng ban được chọn
                # có thuộc phòng ban được cấu hình của user hay không
                list_department = func.get_child_id(self.env.user.department_id, 'hrm_departments',
                                                    'superior_department')
                for depart in self.department_id:
                    if depart.id not in list_department:
                        raise AccessDenied(f"Bạn không có quyền cấu hình phòng ban {depart.name}")
        elif self.env.user.block_id == constraint.BLOCK_COMMERCE_NAME:
            # nếu là khối thương mại
            if self.env.user.company or self.company:
                list_company = func.get_child_id(self.env.user.company, 'hrm_companies', 'parent_company')
                for sys in self.env.user.system_id:
                    list_company += func._system_have_child_company(sys.id)
                for com in self.company:
                    if com.id not in list_company:
                        raise AccessDenied(f"Bạn không có quyền cấu hình công ty {com.name}")
            elif self.env.user.system_id and not self.env.user.company:
                list_system = func.get_child_id(self.env.user.system_id, 'hrm_systems', 'parent_system')
                for sys in self.system_id:
                    if sys.id not in list_system:
                        raise AccessDenied(f"Bạn không có quyền cấu hình hệ thống {sys.name}")
        if self.block_id.name != self.env.user.block_id and self.env.user.block_id != "full":
            # nếu không kiểm tra xem khối được chọn có phải là khối được cấu hình hay không
            raise AccessDenied(f"Bạn không có quyền cấu hình khối {self.block_id.name}.")


class Approve(models.Model):
    _name = 'hrm.approval.flow'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    approval_id = fields.Many2one('hrm.approval.flow.object')
    step = fields.Integer(string='Bước', default=1, order='step')
    approve = fields.Many2one('res.users', string='Người phê duyệt', required=True, tracking=True)
    obligatory = fields.Boolean(string='Bắt buộc')
    excess_level = fields.Boolean(string='Vượt cấp')


class ApproveProfile(models.Model):
    _name = 'hrm.approval.flow.profile'
    _inherit = 'hrm.approval.flow'

    profile_id = fields.Many2one('hrm.employee.profile')
    approve_status = fields.Selection(constraint.APPROVE_STATUS, default='pending', string="Trạng thái")
    time = fields.Datetime(string="Thời gian")
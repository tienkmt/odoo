from odoo import models, fields, api
from . import constraint


class Users(models.Model):
    _inherit = 'res.users'

    block_id = fields.Selection(selection=[
        ('full', 'Tất cả khối'),
        (constraint.BLOCK_OFFICE_NAME, constraint.BLOCK_OFFICE_NAME),
        (constraint.BLOCK_COMMERCE_NAME, constraint.BLOCK_COMMERCE_NAME)], string="Khối phân quyền",
        default=constraint.BLOCK_COMMERCE_NAME, required=True)
    department_id = fields.Many2many('hrm.departments', string='Phòng/Ban')
    system_id = fields.Many2many('hrm.systems', string='Hệ thống')
    company = fields.Many2many('hrm.companies', string='Công ty')
    related = fields.Boolean(compute='_compute_related_')

    user_name_display = fields.Char('Tên hiển thị', readonly=True, store=True)
    user_block_id = fields.Many2one('hrm.blocks', string='Khối', required=True,
                                    default=lambda self: self.default_block())
    user_department_id = fields.Many2one('hrm.departments', string='Phòng ban')
    user_system_id = fields.Many2one('hrm.systems', string='Hệ thống')
    user_code = fields.Char(string="Mã nhân viên")
    user_position_id = fields.Many2one('hrm.position', string='Vị trí', required=True)

    def default_teams(self):
        return [('id', '=', 0)]

    user_team_marketing = fields.Many2one('hrm.teams', string='Đội ngũ marketing', domain=default_teams)
    user_team_sales = fields.Many2one('hrm.teams', string='Đội ngũ bán hàng', domain=default_teams)
    user_phone_num = fields.Char('Số điện thoại', required=True)
    user_related = fields.Boolean(compute='compute_related')
    require_team = fields.Boolean(default=False)

    def default_block(self):
        """Đặt giá trị mặc định cho trường khối của tài khoản nhân sự"""
        return self.env['hrm.blocks'].sudo().search([('name', '=', constraint.BLOCK_COMMERCE_NAME)])

    @api.depends('block_id')
    def _compute_related_(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị
        for record in self:
            record.related = record.block_id == constraint.BLOCK_OFFICE_NAME

    @api.depends('user_block_id')
    def compute_related(self):
        # Lấy giá trị của trường related để check điều kiện hiển thị (thiết lập nhân sự)
        for record in self:
            record.user_related = record.user_block_id.name == constraint.BLOCK_OFFICE_NAME

    @api.onchange('block_id')
    def _onchange_block_id(self):
        self.department_id = self.system_id = self.company = False

    @api.onchange('user_block_id')
    def _onchange_block_id(self):
        """
            Khi chọn lại khối clear hết data cũ đã nhập (thiết lập nhân sự)
        """
        self.user_position_id = self.user_system_id = self.user_company_id = self.user_department_id \
            = self.user_team_sales = self.user_team_marketing = False

    @api.onchange('user_position_id')
    def onchange_position_id(self):
        """
            Khi thay đổi vị trí sẽ check loại đội ngũ hiển thị là gì.
        """
        if self.user_position_id.team_type == 'marketing':
            self.require_team = True
        else:
            self.require_team = False

    @api.onchange('system_id')
    def _onchange_system_id(self):
        """
            decorator này khi tạo hồ sơ nhân viên, chọn 1 hệ thống nào đó
            khi ta chọn cty nó sẽ hiện ra tất cả những cty có trong hệ thống đó
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
            list_id = []
            for sys in self.system_id.ids:
                func = self.env['hrm.utils']
                list_id += func._system_have_child_company(sys)
            return {'domain': {'company': [('id', 'in', list_id)]}}
        self.company = [(6, 0, [])]

    def _remove_system_not_have_company(self):
        """
            Xóa hệ thống không có công ty
        """
        if self.company:
            list_system_ids = self.system_id.ids
            for sys in self.system_id.ids:
                func = self.env['hrm.utils']
                if not any(company in func._system_have_child_company(sys) for company in self.company.ids):
                    self.system_id = [(6, 0, list_system_ids)]

    def write(self, vals):
        res = super(Users, self).write(vals)
        self._remove_system_not_have_company()
        if 'name' in list(vals.keys()) and self.env.user.id == self.id:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        return res

    @api.model
    def create(self, vals_list):
        res = super(Users, self).create(vals_list)
        self._remove_system_not_have_company()
        return res

    # @api.depends('name', 'user_position_id', 'user_company_id')
    # def _compute_user_display_name(self):
    #     name_f = ''
    #     if self.name and self.user_position_id and self.user_company_id:
    #             name_f = self.name + "_" + self.user_position_id.work_position  + "_" + self.user_company_id.name
    #     elif self.name and self.user_position_id and self.user_department_id:
    #             name_f = f'{self.name}_{self.user_position_id.work_position}_{self.user_department_id.name}'
    #     self.user_name_display = name_f

    def get_child_company(self):
        """ lấy tất cả công ty user được cấu hình trong thiết lập """
        list_child_company = []
        if self.env.user.user_company_id:
            # nếu user đc cấu hình công ty thì lấy list id công ty con của công ty đó
            list_child_company = self.env['hrm.utils'].get_child_id(self.env.user.user_company_id, 'hrm_companies',
                                                                    "parent_company")
        elif not self.env.user.user_company_id and self.env.user.user_system_id:
            # nếu user chỉ đc cấu hình hệ thống
            # lấy list id công ty con của hệ thống đã chọn
            func = self.env['hrm.utils']
            for sys in self.env.user.user_system_id:
                list_child_company += func._system_have_child_company(sys.id)
        return [('id', 'in', list_child_company)]

    user_company_id = fields.Many2one('hrm.companies', string="Công ty", tracking=True, domain=get_child_company)

    @api.onchange('user_system_id')
    def _onchange_system_id(self):
        if self.user_system_id:
            system = self.user_system_id
            child_company_ids = []

            # Lấy danh sách các ID của các công ty liên quan đến hệ thống đã chọn
            func = self.env['hrm.utils']
            child_company_ids += func._system_have_child_company(system.id)

            # Cập nhật miền của trường 'user_company_id' để chỉ hiển thị các công ty liên quan đến hệ thống đã chọn
            return {'domain': {'user_company_id': [('id', 'in', child_company_ids)]}}

    @api.onchange('user_block_id')
    def _onchange_user_block_id(self):
        """
        Phương thức này được kích hoạt khi trường 'user_block_id' thay đổi.
        Nó cập nhật các tùy chọn có sẵn cho trường 'user_position_id' dựa trên 'user_block_id' được chọn.
        """
        if self.user_block_id:
            # Tìm tất cả các vị trí thuộc khối đã chọn
            cac_vi_tri = self.env['hrm.position'].search([('block', '=', self.user_block_id.name)])

            # Cập nhật miền của 'user_position_id' để giới hạn các tùy chọn cho khối đã chọn
            return {'domain': {'user_position_id': [('id', 'in', cac_vi_tri.ids)]}}
        else:
            # Nếu không có khối nào được chọn, xóa bộ lọc
            return {'domain': {'user_position_id': []}}

    @api.onchange('user_department_id')
    def _default_position_1(self):
        if self.user_block_id.name == constraint.BLOCK_OFFICE_NAME:
            self.user_position_id = False
            if self.user_department_id:
                position = self.env['hrm.position'].search([('department', '=', self.user_department_id.id)])
                return {'domain': {'user_position_id': [('id', 'in', position.ids)]}}

    @api.onchange('user_company_id')
    def _onchange_company(self):
        """decorator này tạo hồ sơ nhân viên, chọn cty cho hồ sơ đó
             sẽ tự hiển thị đội ngũ mkt và sale nó thuộc vào
        """
        self.user_team_marketing = self.user_team_sales = False
        if self.user_company_id:
            list_team_marketing = self.env['hrm.teams'].search(
                [('company', '=', self.user_company_id.id), ('type_team', '=', 'marketing')])
            list_team_sale = self.env['hrm.teams'].search(
                [('company', '=', self.user_company_id.id), ('type_team', 'in', ('sale', 'resale'))])

            return {
                'domain': {
                    'user_team_marketing': [('id', 'in', list_team_marketing.ids)],
                    'user_team_sales': [('id', 'in', list_team_sale.ids)]
                }
            }
        else:
            return {}
        self.user_system_id = self.user_company_id.system_id
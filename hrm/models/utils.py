from odoo import models
from . import constraint


class Utils(models.Model):
    _name = 'hrm.utils'

    def default_block_(self):
        # Đặt giá trị mặc định cho Khối -> Khối thương mại
        if self.env.user.block_id == constraint.BLOCK_OFFICE_NAME:
            return self.env['hrm.blocks'].search([('name', '=', constraint.BLOCK_OFFICE_NAME)]).id
        else:
            return self.env['hrm.blocks'].search([('name', '=', constraint.BLOCK_COMMERCE_NAME)]).id

    def get_child_id(self, _object, table_name, parent):
        """
            Truy vấn tất cả các các phần tử là con
            _object là danh sách đối tượng cần truy vấn
            table_name là tên bảng
            parent là tên cột cha
        """
        list_object = []
        for ob in _object:
            query = f"""
                WITH RECURSIVE subordinates AS (
                SELECT id, {parent}
                FROM {table_name}
                WHERE id = {ob.id}
                UNION ALL
                SELECT t.id, t.{parent}
                FROM {table_name} t
                INNER JOIN subordinates s ON t.{parent} = s.id
            )
            SELECT id FROM subordinates;
            """
            self._cr.execute(query)
            temp = self._cr.fetchall()
            temp = [obj[0] for obj in temp]
            for t in temp:
                list_object.append(t)
        return list_object

    def _system_have_child_company(self, system_id):
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

    def _see_record_with_config(self, db_name):
        """Nhìn thấy tất cả bản ghi trong màn hình tạo mới hồ sơ theo cấu hình quyền"""
        self.env[db_name].sudo().search([('see_record_with_config', '=', True)]).write(
            {'see_record_with_config': False})
        user = self.env.user
        # Tim tat ca cac cong ty, he thong, phong ban con
        company_config = self.get_child_id(user.company, 'hrm_companies', "parent_company")
        system_config = self.get_child_id(user.system_id, 'hrm_systems', "parent_system")
        department_config = self.get_child_id(user.department_id, 'hrm_departments',
                                                               "superior_department")
        block_config = user.block_id
        domain = []
        # Lay domain theo cac truong
        if not user.has_group("hrm.hrm_group_create_edit"):
            if company_config:
                domain.append(('company', 'in', company_config))
            elif system_config:
                domain.append(('system_id', 'in', system_config))
            elif department_config:
                domain.append(('department_id', 'in', department_config))
            elif block_config:
                # Neu la full thi domain = []
                if block_config != 'full':
                    block_id = self.env['hrm.blocks'].search([('name', '=', block_config)], limit=1)
                    if block_id:
                        domain.append(('block_id', '=', block_id.id))

            self.env[db_name].sudo().search(domain).write({'see_record_with_config': True})

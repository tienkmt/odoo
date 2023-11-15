from odoo import models, fields, api


class ConfirmUpdateDocument(models.TransientModel):
    _name = 'hrm.confirm_update_document'
    _description = 'Xác nhận cập nhật tài liệu'

    UPDATE_CONFIRM_DOCUMENT = [
        ('all', 'Áp dụng tất cả hồ sơ.'),
        ('not_approved_and_new', 'Áp dụng cho hồ sơ chưa được phê duyệt và nháp.'),
        ('new', 'Áp dụng cho hồ sơ trạng thái nháp.')
    ]

    update_confirm_document = fields.Selection(selection=UPDATE_CONFIRM_DOCUMENT, string="Cập nhật tài liệu",
                                               required=True)
    number_applicable_records = fields.Integer(string="Số hồ sơ được áp dụng",
                                               compute='_compute_number_applicable_records', default=0)

    def _get_record_employee_ids(self, document_config, state: list):
        if state:
            query = f"""
                    SELECT id FROM hrm_employee_profile 
                    WHERE document_config = {document_config} AND state IN {tuple(state)}
                    """
            self._cr.execute(query)
        else:
            query = f"""
                    SELECT id FROM hrm_employee_profile 
                    WHERE document_config = {document_config}
                    """
            self._cr.execute(query)
        list_id = [i[0] for i in self._cr.fetchall()]
        return list_id

    def action_confirm_update_document(self):
        # lấy bản ghi đang được chọn và gọi action update document
        id_record = self.env.context.get('active_id')
        record = self.env['hrm.document.list.config'].sudo().browse(id_record)
        # khi lựa chọn 1 trong 3 option trên popup thì cho phép tính lại
        # danh sách tài liệu của HSNS
        if self.update_confirm_document == 'all':
            record_employee_ids = self._get_record_employee_ids(id_record, [])
            self.env['hrm.employee.profile'].sudo().browse(record_employee_ids).write(
                {'is_compute_documents_list': True}
            )
            return record.action_update_document('all')
        elif self.update_confirm_document == 'not_approved_and_new':
            record_employee_ids = self._get_record_employee_ids(id_record, ['draft', 'pending'])
            self.env['hrm.employee.profile'].sudo().browse(record_employee_ids).write(
                {'is_compute_documents_list': True}
            )
            return record.action_update_document('not_approved_and_new')
        else:
            #state khi truyền vào hàm cần là 1 list trên 2 phần tử vì sau đó sẽ dùng tuple(state)
            record_employee_ids = self._get_record_employee_ids(id_record, ['draft', 'false'])
            self.env['hrm.employee.profile'].sudo().browse(record_employee_ids).write(
                {'is_compute_documents_list': True}
            )
            return record.action_update_document('new')

    @api.depends('update_confirm_document')
    def _compute_number_applicable_records(self):
        id_record = self.env.context.get('active_id')
        if self.update_confirm_document == 'all':
            record_employee_ids = self._get_record_employee_ids(id_record, [])
            self.number_applicable_records = len(record_employee_ids)
        elif self.update_confirm_document == 'not_approved_and_new':
            record_employee_ids = self._get_record_employee_ids(id_record, ['draft', 'pending'])
            self.number_applicable_records = len(record_employee_ids)
        else:
            # state khi truyền vào hàm cần là 1 list trên 2 phần tử vì sau đó sẽ dùng tuple(state)
            record_employee_ids = self._get_record_employee_ids(id_record, ['draft', 'false'])
            self.number_applicable_records = len(record_employee_ids)

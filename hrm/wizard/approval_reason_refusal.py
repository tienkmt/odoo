from odoo import models, fields


class ApprovalReasonRefusal(models.TransientModel):
    _name = "approval.reason.refusal"
    _description = "Lý do từ chối"

    reason_refusal = fields.Char(string="Lý do từ chối", required=True)

    def action_approval_reason_refusal(self):
        # lấy bản ghi đang được chọn và gọi action từ chối
        leads = self.env['hrm.employee.profile'].sudo().browse(self.env.context.get('active_ids'))
        return leads.action_refuse(self.reason_refusal)

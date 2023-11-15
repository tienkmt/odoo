from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
import re
from . import constraint


class Documents(models.Model):
    _name = 'hrm.documents'
    _description = 'Tài liệu'

    name = fields.Char(string='Tên hiển thị', required=True)
    document_code = fields.Char(string='Mã tài liệu', required=True)
    numbers_of_photos = fields.Char(string='Số lượng ảnh', required=True)
    numbers_of_documents = fields.Char(string='Số lượng tài liệu', required=True)

    @api.constrains('numbers_of_photos', 'numbers_of_documents')
    def check_negative_numbers(self):
        if self.numbers_of_photos and not re.match(r'^[0-9]+$', self.numbers_of_photos):
            raise ValidationError('Số ảnh chỉ được chứa số.')

        if self.numbers_of_documents and not re.match(r'^[0-9]+$', self.numbers_of_documents):
            raise ValidationError('Số tệp chỉ được chứa số.')



    @api.onchange('numbers_of_photos', 'numbers_of_documents')
    def check_negative_numbers(self):
        if self.numbers_of_photos and not re.match(r'^[0-9]+$', self.numbers_of_photos):
            raise ValidationError('Số ảnh chỉ được chứa số và không âm.')

        if self.numbers_of_documents and not re.match(r'^[0-9]+$', self.numbers_of_documents):
            raise ValidationError('Số tệp đính kèm chỉ được chứa số và không âm.')



    @api.constrains('name')
    def check_duplicate_name(self):
        for record in self:
            name = self.search([('id', '!=', record.id)])
            for n in name:
                if n['name'].lower() == record.name.lower():
                    raise ValidationError(constraint.DUPLICATE_RECORD % "Tài liệu")

BLOCK_OFFICE_NAME = "Văn phòng"
BLOCK_COMMERCE_NAME = "Thương mại"

SELECT_TYPE_COMPANY = [
    ('sale', 'Sale'),
    ('upsale', 'Upsale')
]

SELECT_TYPE_TEAM = [
    ('marketing', 'Marketing'),
    ('sale', 'Sale'),
    ('resale', 'Resale')
]

PROFILE_STATUS = [
    ('incomplete', 'Chưa hoàn thiện'),
    ('complete', 'Hoàn thiện')
]

STATE = [
    ('draft', 'Nháp'),
    ('pending', 'Chờ duyệt'),
    ('approved', 'Đã duyệt')
]

STATE_REOPEN = [
    ('wait_reopen', 'Chờ mở lại'),
    ('active_reopen', 'Đang hoạt động'),
    ('close', 'Đã đóng'),
    ('cancel', 'Hủy')
]

APPROVE_STATUS = [
    ('pending', 'Chờ duyệt'),
    ('confirm', 'Đã duyệt'),
    ('refuse', 'Từ chối'),
    ('confirm_excess_level', 'Duyệt vượt cấp')
]

TYPE_SYSTEM = [
    ('sale', 'Sale'),
    ('resale', 'Resale')
]

UPDATE_CONFIRM_DOCUMENT = [
    ('all', 'Áp dụng tất cả hồ sơ.'),
    ('not_approved_and_new', 'Áp dụng cho hồ sơ chưa được phê duyệt và hồ sơ mới.'),
    ('new', 'Áp dụng cho hồ sơ mới.')
]

ERROR_NAME = "Tên %s không được chứa ký tự đặc biệt."
ERROR_PHONE = "Số điện thoại không hợp lệ"
DO_NOT_DELETE = "Không thể xoá bản ghi này!"
DO_NOT_ARCHIVE = "Không thể lưu trữ bản ghi này!"
DUPLICATE_RECORD = '%s đã tồn tại!'

from odoo import models, fields, api
from datetime import datetime, time
from odoo.exceptions import ValidationError
from pytz import timezone, UTC

class TrangThaiChamCong(models.Model):
    _name = 'trang_thai_cham_cong'
    _description = 'Trạng thái chấm công'

    name = fields.Char(string="Tên trạng thái", required=True)


class BangChamCong(models.Model):
    _name = 'bang_cham_cong'
    _description = "Bảng chấm công"
    _rec_name = 'Id_BCC'

    # Basic fields
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_cham_cong = fields.Date("Ngày chấm công", required=True)

    Id_BCC = fields.Char(string="ID BCC", compute="_compute_Id_BCC", store=True)

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_Id_BCC(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                record.Id_BCC = f"{record.nhan_vien_id.ho_va_ten}_{record.ngay_cham_cong.strftime('%Y-%m-%d')}"
            else:
                record.Id_BCC = ""
    
    # Đăng ký ca làm
    dang_ky_ca_lam_id = fields.Many2one('dang_ky_ca_lam_theo_ngay', string="Đăng ký ca làm")
    ca_lam = fields.Selection(related='dang_ky_ca_lam_id.ca_lam', store=True, string="Ca làm")

    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_dang_ky_ca_lam(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_lam', '=', record.ngay_cham_cong)
                ], limit=1)
                record.dang_ky_ca_lam_id = dk_ca_lam.id if dk_ca_lam else False
            else:
                record.dang_ky_ca_lam_id = False

    @api.model
    def create(self, vals):
        # Xử lý dang_ky_ca_lam_id
        if vals.get('nhan_vien_id') and vals.get('ngay_cham_cong'):
            # Tìm đăng ký ca làm
            dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_lam', '=', vals['ngay_cham_cong'])
            ], limit=1)
            if dk_ca_lam:
                vals['dang_ky_ca_lam_id'] = dk_ca_lam.id
            
            # Tìm đơn từ
            don_tu = self.env['don_tu'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_ap_dung', '=', vals['ngay_cham_cong']),
                ('trang_thai_duyet', '=', 'da_duyet')
            ], limit=1)
            if don_tu:
                vals['don_tu_id'] = don_tu.id
            
        return super(BangChamCong, self).create(vals)

    def write(self, vals):
        for record in self:
            # Lấy giá trị mới hoặc giữ giá trị cũ
            nhan_vien_id = vals.get('nhan_vien_id', record.nhan_vien_id.id)
            ngay_cham_cong = vals.get('ngay_cham_cong', record.ngay_cham_cong)
            
            if nhan_vien_id and ngay_cham_cong:
                # Tìm đăng ký ca làm
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_lam', '=', ngay_cham_cong)
                ], limit=1)
                vals['dang_ky_ca_lam_id'] = dk_ca_lam.id if dk_ca_lam else False
            
                # Tìm đơn từ
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_ap_dung', '=', ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet')
                ], limit=1)
                vals['don_tu_id'] = don_tu.id if don_tu else False
            
        return super(BangChamCong, self).write(vals)

    # Thời gian làm việc
    gio_vao_ca = fields.Datetime("Giờ vào ca", compute='_compute_gio_ca', store=True)
    gio_ra_ca = fields.Datetime("Giờ ra ca", compute='_compute_gio_ca', store=True)
    
    @api.depends('ca_lam', 'ngay_cham_cong')
    def _compute_gio_ca(self):
        for record in self:
            if not record.ngay_cham_cong or not record.ca_lam:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            user_tz = self.env.user.tz or 'UTC'
            tz = timezone(user_tz)

            if record.ca_lam == "Sáng":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(11, 30)  # 11:30 AM
            elif record.ca_lam == "Chiều":
                gio_vao = time(13, 30)  # 1:30 PM
                gio_ra = time(17, 30)  # 5:30 PM
            elif record.ca_lam == "Cả ngày":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(17, 30)  # 5:30 PM
            else:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            # Convert to datetime in user's timezone
            naive_vao = datetime.combine(record.ngay_cham_cong, gio_vao)
            naive_ra = datetime.combine(record.ngay_cham_cong, gio_ra)
            
            # Store in UTC
            record.gio_vao_ca = tz.localize(naive_vao).astimezone(UTC).replace(tzinfo=None)
            record.gio_ra_ca = tz.localize(naive_ra).astimezone(UTC).replace(tzinfo=None)

    gio_vao = fields.Datetime("Giờ vào thực tế")
    gio_ra = fields.Datetime("Giờ ra thực tế")

    # Tính toán đi muộn
    phut_di_muon_goc = fields.Float("Số phút đi muộn gốc", compute="_compute_phut_di_muon_goc", store=True)
    phut_di_muon = fields.Float("Số phút đi muộn thực tế", compute="_compute_phut_di_muon", store=True)
    
    @api.depends('gio_vao', 'gio_vao_ca')
    def _compute_phut_di_muon_goc(self):
        for record in self:
            if record.gio_vao and record.gio_vao_ca:
                delta = record.gio_vao - record.gio_vao_ca
                record.phut_di_muon_goc = max(0, delta.total_seconds() / 60)
            else:
                record.phut_di_muon_goc = 0

    @api.depends('phut_di_muon_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_di_muon(self):
        for record in self:
            record.phut_di_muon = record.phut_di_muon_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 'di_muon':
                    record.phut_di_muon = max(0, record.phut_di_muon_goc - record.thoi_gian_xin)
                elif record.loai_don == 'di_muon_ve_som':
                    thoi_gian_moi_ben = record.thoi_gian_xin / 2
                    record.phut_di_muon = max(0, record.phut_di_muon_goc - thoi_gian_moi_ben)

    # Tính toán về sớm
    phut_ve_som_goc = fields.Float("Số phút về sớm gốc", compute="_compute_phut_ve_som_goc", store=True)
    phut_ve_som = fields.Float("Số phút về sớm thực tế", compute="_compute_phut_ve_som", store=True)
    
    @api.depends('gio_ra', 'gio_ra_ca')
    def _compute_phut_ve_som_goc(self):
        for record in self:
            if record.gio_ra and record.gio_ra_ca:
                delta = record.gio_ra_ca - record.gio_ra
                record.phut_ve_som_goc = max(0, delta.total_seconds() / 60)
            else:
                record.phut_ve_som_goc = 0

    @api.depends('phut_ve_som_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_ve_som(self):
        for record in self:
            record.phut_ve_som = record.phut_ve_som_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 've_som':
                    record.phut_ve_som = max(0, record.phut_ve_som_goc - record.thoi_gian_xin)
                elif record.loai_don == 'di_muon_ve_som':
                    thoi_gian_moi_ben = record.thoi_gian_xin / 2
                    record.phut_ve_som = max(0, record.phut_ve_som_goc - thoi_gian_moi_ben)

    # Trạng thái chấm công
    trang_thai = fields.Selection([
        ('di_lam', 'Đi làm'),
        ('di_muon', 'Đi muộn'),
        ('di_muon_ve_som', 'Đi muộn và về sớm'),
        ('ve_som', 'Về sớm'),
        ('vang_mat', 'Vắng mặt'),
        ('vang_mat_co_phep', 'Vắng mặt có phép'),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True)
    
    @api.depends('phut_di_muon', 'phut_ve_som', 'gio_vao', 'gio_ra')
    def _compute_trang_thai(self):
        for record in self:
            if not record.gio_vao and not record.gio_ra:
                record.trang_thai = 'vang_mat'
            elif record.phut_di_muon > 0:
                record.trang_thai = 'di_muon'
            elif record.phut_di_muon > 0 and record.phut_ve_som > 0:
                record.trang_thai = 'di_muon_ve_som'
            elif record.phut_ve_som > 0:
                record.trang_thai = 've_som'
            else:
                record.trang_thai = 'di_lam'

    # Đơn từ liên quan
    don_tu_id = fields.Many2one('don_tu', string="Đơn từ")
    loai_don = fields.Selection(string='Loại đơn',related='don_tu_id.loai_don')
    thoi_gian_xin = fields.Float(string='Thời gian xin',related='don_tu_id.thoi_gian_xin')
    
    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_don_tu(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_ap_dung', '=', record.ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet')
                ], limit=1)
                record.don_tu_id = don_tu.id if don_tu else False
            else:
                record.don_tu_id = False

    
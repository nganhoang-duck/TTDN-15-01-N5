from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DangKyCaLamTheoNgay(models.Model):
    _name = 'dang_ky_ca_lam_theo_ngay'
    _description = "Đăng ký ca làm theo ngày"
    _rec_name = 'dang_ky_ca_lam_id'
    _order = 'dot_dang_ky_id desc, ngay_lam asc'

    dang_ky_ca_lam_id = fields.Char("Mã đăng ký theo ngày", compute="_compute_ma_dang_ky")
    dot_dang_ky_id = fields.Many2one('dot_dang_ky', string="Đợt đăng ký", required=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_lam = fields.Date(string="Ngày làm", required=True)
    ca_lam = fields.Selection([
        ("Sáng", "Sáng"),
        ("Chiều", "Chiều"),
        ("Cả ngày", "Cả Ngày"),
    ], string="Ca làm", default="")
    
    @api.depends("nhan_vien_id", "ngay_lam")
    def _compute_ma_dang_ky(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_lam:
                record.dang_ky_ca_lam_id = f"{record.nhan_vien_id.ho_va_ten} - {record.ngay_lam.strftime('%d/%m/%Y')}"
            else:
                record.dang_ky_ca_lam_id = ""

    @api.constrains('ngay_lam', 'dot_dang_ky_id')
    def _check_ngay_lam(self):
        for record in self:
            if record.ngay_lam and record.dot_dang_ky_id:
                if record.ngay_lam < record.dot_dang_ky_id.ngay_bat_dau or record.ngay_lam > record.dot_dang_ky_id.ngay_ket_thuc:
                    raise ValidationError(f'Ngày làm phải nằm trong khoảng thời gian của đợt đăng ký (từ {record.dot_dang_ky_id.ngay_bat_dau} đến {record.dot_dang_ky_id.ngay_ket_thuc})')

    @api.constrains('nhan_vien_id', 'dot_dang_ky_id')
    def _check_nhan_vien_in_dot_dang_ky(self):
        for record in self:
            if record.nhan_vien_id not in record.dot_dang_ky_id.nhan_vien_ids:
                raise ValidationError(f'Nhân viên {record.nhan_vien_id.ho_va_ten} không thuộc đợt đăng ký này!')

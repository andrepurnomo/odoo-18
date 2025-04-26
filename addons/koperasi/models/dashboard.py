# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.tools import SQL


class KoperasiDashboard(models.Model):
    _name = 'koperasi.dashboard'
    _description = 'Dashboard Koperasi'

    # Dashboard fields - updated with compute methods
    total_anggota_aktif = fields.Integer(
        string='Total Anggota Aktif', compute='_compute_anggota_stats', store=True, precompute=True)
    total_anggota_baru_bulan_ini = fields.Integer(
        string='Anggota Baru Bulan Ini', compute='_compute_anggota_stats', store=True, precompute=True)

    total_simpanan = fields.Monetary(
        string='Total Simpanan', compute='_compute_simpanan_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_simpanan_pokok = fields.Monetary(
        string='Total Simpanan Pokok', compute='_compute_simpanan_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_simpanan_wajib = fields.Monetary(
        string='Total Simpanan Wajib', compute='_compute_simpanan_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_simpanan_sukarela = fields.Monetary(
        string='Total Simpanan Sukarela', compute='_compute_simpanan_stats', currency_field='currency_id',
        store=True, precompute=True)

    total_pinjaman_aktif_count = fields.Integer(
        string='Total Pinjaman Aktif', compute='_compute_pinjaman_stats', store=True, precompute=True)
    total_pinjaman_pengajuan_count = fields.Integer(
        string='Total Pengajuan Pinjaman', compute='_compute_pinjaman_stats', store=True, precompute=True)
    total_pinjaman_menunggak_count = fields.Integer(
        string='Total Pinjaman Menunggak', compute='_compute_pinjaman_stats', store=True, precompute=True)
    total_pinjaman_aktif = fields.Monetary(
        string='Total Nilai Pinjaman Aktif', compute='_compute_pinjaman_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_pendapatan_bunga_tahun_ini = fields.Monetary(
        string='Total Pendapatan Bunga Tahun Ini', compute='_compute_pendapatan_bunga', currency_field='currency_id',
        store=True, precompute=True)

    total_angsuran_jatuh_tempo_hari_ini_count = fields.Integer(
        string='Total Angsuran Jatuh Tempo Hari Ini', compute='_compute_angsuran_stats',
        store=True, precompute=True)
    total_angsuran_telat_count = fields.Integer(
        string='Total Angsuran Telat', compute='_compute_angsuran_stats',
        store=True, precompute=True)
    total_angsuran_jatuh_tempo_hari_ini = fields.Monetary(
        string='Nilai Angsuran Jatuh Tempo Hari Ini', compute='_compute_angsuran_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_angsuran_telat = fields.Monetary(
        string='Nilai Tunggakan', compute='_compute_angsuran_stats', currency_field='currency_id',
        store=True, precompute=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Default singleton record
    @api.model
    def _get_default_id(self):
        dashboard_id = self.search([('id', '=', 1)])
        if not dashboard_id:
            dashboard_id = self.create({})
        return dashboard_id

    @api.model
    def get_dashboard_data(self):
        dashboard_id = self._get_default_id()
        return {
            'id': dashboard_id.id,
        }

    @api.depends()
    def _compute_anggota_stats(self):
        for record in self:
            # Total anggota aktif
            record.total_anggota_aktif = self.env['koperasi.anggota'].search_count([
                ('status_keanggotaan', '=', 'aktif')
            ])

            # Anggota baru bulan ini
            first_day_of_month = date.today().replace(day=1)
            record.total_anggota_baru_bulan_ini = self.env['koperasi.anggota'].search_count([
                ('tanggal_bergabung', '>=', first_day_of_month),
                ('tanggal_bergabung', '<=', date.today())
            ])

    @api.depends()
    def _compute_simpanan_stats(self):
        for record in self:
            simpanan_domain = [('saldo', '>', 0)]

            # Total semua simpanan
            simpanan_data = self.env['koperasi.simpanan'].search(
                simpanan_domain)
            record.total_simpanan = sum(simpanan_data.mapped('saldo'))

            # Simpanan berdasarkan jenis
            record.total_simpanan_pokok = sum(simpanan_data.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'pokok').mapped('saldo'))
            record.total_simpanan_wajib = sum(simpanan_data.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'wajib').mapped('saldo'))
            record.total_simpanan_sukarela = sum(simpanan_data.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'sukarela').mapped('saldo'))

    @api.depends()
    def _compute_pinjaman_stats(self):
        for record in self:
            # Total pinjaman aktif
            pinjaman_aktif = self.env['koperasi.pinjaman'].search([
                ('status_pinjaman', '=', 'aktif')
            ])
            record.total_pinjaman_aktif_count = len(pinjaman_aktif)
            record.total_pinjaman_aktif = sum(
                pinjaman_aktif.mapped('sisa_pinjaman'))

            # Total pengajuan pinjaman
            record.total_pinjaman_pengajuan_count = self.env['koperasi.pinjaman'].search_count([
                ('status_pinjaman', '=', 'pengajuan')
            ])

            # Total pinjaman menunggak
            record.total_pinjaman_menunggak_count = self.env['koperasi.pinjaman'].search_count([
                ('status_pinjaman', '=', 'menunggak')
            ])

    @api.depends()
    def _compute_pendapatan_bunga(self):
        for record in self:
            # Pendapatan bunga tahun ini
            tahun_sekarang = str(date.today().year)
            angsuran_dibayar = self.env['koperasi.angsuran.pinjaman'].search([
                ('status_pembayaran', 'in', ['sudah_bayar', 'telat_bayar']),
                ('tanggal_pembayaran', '>=', f'{tahun_sekarang}-01-01'),
                ('tanggal_pembayaran', '<=', f'{tahun_sekarang}-12-31')
            ])
            record.total_pendapatan_bunga_tahun_ini = sum(
                angsuran_dibayar.mapped('jumlah_bunga_angsuran'))

    @api.depends()
    def _compute_angsuran_stats(self):
        for record in self:
            today = date.today()

            # Angsuran jatuh tempo hari ini
            angsuran_hari_ini = self.env['koperasi.angsuran.pinjaman'].search([
                ('tanggal_jatuh_tempo', '=', today),
                ('status_pembayaran', '=', 'belum_bayar')
            ])
            record.total_angsuran_jatuh_tempo_hari_ini_count = len(
                angsuran_hari_ini)
            record.total_angsuran_jatuh_tempo_hari_ini = sum(
                angsuran_hari_ini.mapped('total_angsuran_bulan'))

            # Angsuran telat
            angsuran_telat = self.env['koperasi.angsuran.pinjaman'].search([
                ('tanggal_jatuh_tempo', '<', today),
                ('status_pembayaran', '=', 'belum_bayar')
            ])
            record.total_angsuran_telat_count = len(angsuran_telat)
            record.total_angsuran_telat = sum(
                angsuran_telat.mapped('total_angsuran_bulan'))

    # Action methods for buttons
    def action_view_anggota_aktif(self):
        return {
            'name': _('Anggota Aktif'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.anggota',
            'view_mode': 'list,form',
            'domain': [('status_keanggotaan', '=', 'aktif')],
        }

    def action_view_anggota_baru(self):
        first_day_of_month = date.today().replace(day=1)
        return {
            'name': _('Anggota Baru Bulan Ini'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.anggota',
            'view_mode': 'list,form',
            'domain': [
                ('tanggal_bergabung', '>=', first_day_of_month),
                ('tanggal_bergabung', '<=', date.today())
            ],
        }

    def action_view_simpanan(self):
        return {
            'name': _('Simpanan'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.simpanan',
            'view_mode': 'list,form',
            'domain': [('saldo', '>', 0)],
        }

    def action_view_pinjaman_aktif(self):
        return {
            'name': _('Pinjaman Aktif'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.pinjaman',
            'view_mode': 'list,form',
            'domain': [('status_pinjaman', '=', 'aktif')],
        }

    def action_view_pinjaman_pengajuan(self):
        return {
            'name': _('Pengajuan Pinjaman'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.pinjaman',
            'view_mode': 'list,form',
            'domain': [('status_pinjaman', '=', 'pengajuan')],
        }

    def action_view_pinjaman_menunggak(self):
        return {
            'name': _('Pinjaman Menunggak'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.pinjaman',
            'view_mode': 'list,form',
            'domain': [('status_pinjaman', '=', 'menunggak')],
        }

    def action_view_angsuran_jatuh_tempo_hari_ini(self):
        return {
            'name': _('Angsuran Jatuh Tempo Hari Ini'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.angsuran.pinjaman',
            'view_mode': 'list,form',
            'domain': [
                ('tanggal_jatuh_tempo', '=', date.today()),
                ('status_pembayaran', '=', 'belum_bayar')
            ],
        }

    def action_view_angsuran_telat(self):
        return {
            'name': _('Angsuran Telah Jatuh Tempo'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.angsuran.pinjaman',
            'view_mode': 'list,form',
            'domain': [
                ('tanggal_jatuh_tempo', '<', date.today()),
                ('status_pembayaran', '=', 'belum_bayar')
            ],
        }

    def action_laporan_shu(self):
        return {
            'name': _('Hitung SHU'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.wizard.hitung.shu',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_laporan_simpanan(self):
        return {
            'name': _('Laporan Simpanan'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.simpanan',
            'view_mode': 'list,form',
            'domain': [],
            'context': {'search_default_group_by_jenis': 1, 'search_default_group_by_anggota': 1},
        }

    def action_laporan_pinjaman(self):
        return {
            'name': _('Laporan Pinjaman'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.pinjaman',
            'view_mode': 'list,form',
            'domain': [('status_pinjaman', 'in', ['aktif', 'menunggak'])],
            'context': {'search_default_group_by_status': 1},
        }

    def action_laporan_tunggakan(self):
        return {
            'name': _('Laporan Tunggakan'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.angsuran.pinjaman',
            'view_mode': 'list,form',
            'domain': [
                ('tanggal_jatuh_tempo', '<', date.today()),
                ('status_pembayaran', '=', 'belum_bayar')
            ],
            'context': {'search_default_group_by_anggota': 1},
        }

    # Additional tax dashboard fields
    total_pajak_bunga_dipotong = fields.Monetary(
        string='Total Pajak Bunga Dipotong', compute='_compute_tax_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_pajak_bulan_ini = fields.Monetary(
        string='Total Pajak Bulan Ini', compute='_compute_tax_stats', currency_field='currency_id',
        store=True, precompute=True)
    total_bunga_bulan_ini = fields.Monetary(
        string='Total Bunga Bulan Ini', compute='_compute_tax_stats', currency_field='currency_id',
        store=True, precompute=True)

    @api.depends()
    def _compute_tax_stats(self):
        for record in self:
            # Current month tax stats
            today = date.today()
            first_day_of_month = today.replace(day=1)
            last_day_of_month = (today.replace(day=1) +
                                 relativedelta(months=1, days=-1))

            # Calculate taxes for the current month
            bulan = today.strftime('%m')
            tahun = today.year

            domain = [
                ('bulan', '=', bulan),
                ('tahun', '=', tahun)
            ]

            pajak_data = self.env['koperasi.pajak.simpanan'].search(domain)

            record.total_pajak_bulan_ini = sum(
                pajak_data.mapped('jumlah_pajak'))
            record.total_bunga_bulan_ini = sum(
                pajak_data.mapped('total_bunga'))

            # Calculate total tax collected all time
            record.total_pajak_bunga_dipotong = self.env['koperasi.pajak.simpanan'].search(
                []).mapped('jumlah_pajak')

    # Add actions
    def action_view_tax_reports(self):
        return {
            'name': _('Laporan Pajak Simpanan'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.pajak.simpanan',
            'view_mode': 'list,form',
            'domain': [],
        }

    def action_pay_interest(self):
        return {
            'name': _('Pembayaran Bunga Simpanan'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.wizard.bayar.bunga',
            'view_mode': 'form',
            'target': 'new',
        }

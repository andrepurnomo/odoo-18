# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from odoo.tools import SQL


class KoperasiAnggota(models.Model):
    _name = 'koperasi.anggota'
    _description = 'Anggota Koperasi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'nomor_anggota'
    _check_company_auto = True

    nomor_anggota = fields.Char(string='Nomor Anggota', required=True, copy=False, readonly=True,
                                default=lambda self: _('New'))
    name = fields.Char(string='Nama Lengkap', required=True,
                       tracking=True, index='trigram')
    nik = fields.Char(string='NIK', required=True, tracking=True)
    alamat = fields.Text(string='Alamat', tracking=True)
    telepon = fields.Char(string='Telepon', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    tanggal_bergabung = fields.Date(
        string='Tanggal Bergabung', default=fields.Date.today, required=True, tracking=True)
    status_keanggotaan = fields.Selection([
        ('aktif', 'Aktif'),
        ('non_aktif', 'Non-Aktif')
    ], string='Status Keanggotaan', default='aktif', required=True, tracking=True)
    tanggal_keluar = fields.Date(string='Tanggal Keluar', tracking=True)

    # Relational fields
    simpanan_ids = fields.One2many(
        'koperasi.simpanan', 'anggota_id', string='Simpanan')
    transaksi_simpanan_ids = fields.One2many(
        'koperasi.transaksi.simpanan', 'anggota_id', string='Riwayat Transaksi')
    pinjaman_ids = fields.One2many(
        'koperasi.pinjaman', 'anggota_id', string='Pinjaman')

    # Computed fields for dashboard
    total_simpanan_pokok = fields.Monetary(compute='_compute_simpanan', string='Total Simpanan Pokok',
                                           currency_field='currency_id', store=True, precompute=True)
    total_simpanan_wajib = fields.Monetary(compute='_compute_simpanan', string='Total Simpanan Wajib',
                                           currency_field='currency_id', store=True, precompute=True)
    total_simpanan_sukarela = fields.Monetary(compute='_compute_simpanan', string='Total Simpanan Sukarela',
                                              currency_field='currency_id', store=True, precompute=True)
    pinjaman_aktif_count = fields.Integer(compute='_compute_pinjaman_stats', string='Pinjaman Aktif',
                                          store=True, precompute=True)
    total_pinjaman_aktif = fields.Monetary(compute='_compute_pinjaman_stats', string='Total Pinjaman Aktif',
                                           currency_field='currency_id', store=True, precompute=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Untuk otentikasi
    user_id = fields.Many2one('res.users', string='Related User')

    _sql_constraints = [
        ('nik_unique', 'UNIQUE(nik)', 'NIK harus unik!'),
        ('nomor_anggota_unique', 'UNIQUE(nomor_anggota)', 'Nomor anggota harus unik!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('nomor_anggota', _('New')) == _('New'):
                vals['nomor_anggota'] = self.env['ir.sequence'].next_by_code(
                    'koperasi.anggota') or _('New')
        return super().create(vals_list)

    @api.constrains('tanggal_keluar', 'status_keanggotaan')
    def _check_tanggal_keluar(self):
        for anggota in self:
            if anggota.status_keanggotaan == 'non_aktif' and not anggota.tanggal_keluar:
                raise ValidationError(
                    _('Anggota non-aktif harus memiliki tanggal keluar.'))
            if anggota.tanggal_keluar and anggota.tanggal_keluar < anggota.tanggal_bergabung:
                raise ValidationError(
                    _('Tanggal keluar tidak boleh sebelum tanggal bergabung.'))

    @api.depends('simpanan_ids', 'simpanan_ids.saldo')
    def _compute_simpanan(self):
        for anggota in self:
            simpanan_pokok = anggota.simpanan_ids.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'pokok')
            simpanan_wajib = anggota.simpanan_ids.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'wajib')
            simpanan_sukarela = anggota.simpanan_ids.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'sukarela')

            anggota.total_simpanan_pokok = sum(
                simpanan_pokok.mapped('saldo')) if simpanan_pokok else 0
            anggota.total_simpanan_wajib = sum(
                simpanan_wajib.mapped('saldo')) if simpanan_wajib else 0
            anggota.total_simpanan_sukarela = sum(
                simpanan_sukarela.mapped('saldo')) if simpanan_sukarela else 0

    @api.depends('pinjaman_ids', 'pinjaman_ids.status_pinjaman', 'pinjaman_ids.total_pinjaman')
    def _compute_pinjaman_stats(self):
        for anggota in self:
            pinjaman_aktif = anggota.pinjaman_ids.filtered(lambda p: p.status_pinjaman in [
                                                           'disetujui', 'aktif', 'menunggak'])
            anggota.pinjaman_aktif_count = len(pinjaman_aktif)
            anggota.total_pinjaman_aktif = sum(
                pinjaman_aktif.mapped('sisa_pinjaman'))

    def action_lihat_simpanan(self):
        return {
            'name': _('Simpanan %s', self.name),
            'view_mode': 'list,form',
            'res_model': 'koperasi.simpanan',
            'domain': [('anggota_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_anggota_id': self.id}
        }

    def action_lihat_pinjaman(self):
        return {
            'name': _('Pinjaman %s', self.name),
            'view_mode': 'list,form',
            'res_model': 'koperasi.pinjaman',
            'domain': [('anggota_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_anggota_id': self.id}
        }

    def action_keluarkan_anggota(self):
        return {
            'name': _('Keluarkan Anggota'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.wizard.keluar.anggota',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_anggota_id': self.id}
        }

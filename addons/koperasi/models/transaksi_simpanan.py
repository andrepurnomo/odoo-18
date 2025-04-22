# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class KoperasiTransaksiSimpanan(models.Model):
    _name = 'koperasi.transaksi.simpanan'
    _description = 'Transaksi Simpanan Koperasi'
    _order = 'tanggal_transaksi desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='ID Transaksi', required=True,
                       copy=False, readonly=True, default=lambda self: _('New'))
    anggota_id = fields.Many2one(
        'koperasi.anggota', string='Anggota', required=True, tracking=True)
    jenis_simpanan_id = fields.Many2one(
        'koperasi.jenis.simpanan', string='Jenis Simpanan', required=True, tracking=True)
    tipe_transaksi = fields.Selection([
        ('setor', 'Setor'),
        ('tarik', 'Tarik'),
        ('potongan_wajib', 'Potongan Wajib'),
        ('pendaftaran_pokok', 'Pendaftaran Pokok'),
        ('pengembalian_keluar', 'Pengembalian Keluar')
    ], string='Tipe Transaksi', required=True, tracking=True)
    jumlah = fields.Monetary(
        string='Jumlah', required=True, currency_field='currency_id', tracking=True)
    tanggal_transaksi = fields.Date(
        string='Tanggal Transaksi', required=True, default=fields.Date.today, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    saldo_sebelum = fields.Monetary(
        string='Saldo Sebelum', currency_field='currency_id', readonly=True)
    saldo_sesudah = fields.Monetary(
        string='Saldo Sesudah', currency_field='currency_id', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'koperasi.transaksi.simpanan') or _('New')
        return super().create(vals_list)

    @api.onchange('anggota_id', 'jenis_simpanan_id')
    def _onchange_anggota_simpanan(self):
        if self.anggota_id and self.jenis_simpanan_id:
            simpanan = self.env['koperasi.simpanan'].search([
                ('anggota_id', '=', self.anggota_id.id),
                ('jenis_simpanan_id', '=', self.jenis_simpanan_id.id)
            ], limit=1)
            if simpanan:
                self.saldo_sebelum = simpanan.saldo

    @api.constrains('tipe_transaksi', 'jumlah', 'anggota_id', 'jenis_simpanan_id')
    def _check_transaksi(self):
        for transaksi in self:
            # Periksa jumlah harus positif
            if transaksi.jumlah <= 0:
                raise ValidationError(
                    _('Jumlah transaksi harus lebih dari 0.'))

            # Jika tipe transaksi tarik atau pengembalian, periksa saldo cukup
            if transaksi.tipe_transaksi in ['tarik', 'pengembalian_keluar']:
                simpanan = self.env['koperasi.simpanan'].search([
                    ('anggota_id', '=', transaksi.anggota_id.id),
                    ('jenis_simpanan_id', '=', transaksi.jenis_simpanan_id.id)
                ], limit=1)

                if not simpanan or simpanan.saldo < transaksi.jumlah:
                    raise ValidationError(
                        _('Saldo tidak cukup untuk melakukan penarikan.'))

    def action_confirm(self):
        for transaksi in self.filtered(lambda t: t.state == 'draft'):
            # Cari atau buat simpanan
            simpanan = self.env['koperasi.simpanan'].search([
                ('anggota_id', '=', transaksi.anggota_id.id),
                ('jenis_simpanan_id', '=', transaksi.jenis_simpanan_id.id)
            ], limit=1)

            # Jika simpanan belum ada, buat baru
            if not simpanan:
                simpanan = self.env['koperasi.simpanan'].create({
                    'anggota_id': transaksi.anggota_id.id,
                    'jenis_simpanan_id': transaksi.jenis_simpanan_id.id,
                    'saldo': 0.0
                })

            # Catat saldo sebelum
            transaksi.saldo_sebelum = simpanan.saldo

            # Update saldo berdasarkan tipe transaksi
            if transaksi.tipe_transaksi in ['setor', 'pendaftaran_pokok', 'potongan_wajib']:
                simpanan.saldo += transaksi.jumlah
            elif transaksi.tipe_transaksi in ['tarik', 'pengembalian_keluar']:
                simpanan.saldo -= transaksi.jumlah

            # Catat saldo sesudah
            transaksi.saldo_sesudah = simpanan.saldo
            simpanan.last_update = fields.Datetime.now()

            # Update status transaksi
            transaksi.state = 'confirmed'

    def action_cancel(self):
        for transaksi in self.filtered(lambda t: t.state == 'confirmed'):
            # Kembalikan saldo ke posisi semula
            simpanan = self.env['koperasi.simpanan'].search([
                ('anggota_id', '=', transaksi.anggota_id.id),
                ('jenis_simpanan_id', '=', transaksi.jenis_simpanan_id.id)
            ], limit=1)

            if simpanan:
                if transaksi.tipe_transaksi in ['setor', 'pendaftaran_pokok', 'potongan_wajib']:
                    simpanan.saldo -= transaksi.jumlah
                elif transaksi.tipe_transaksi in ['tarik', 'pengembalian_keluar']:
                    simpanan.saldo += transaksi.jumlah
                simpanan.last_update = fields.Datetime.now()

            transaksi.state = 'cancelled'

    def action_draft(self):
        for transaksi in self.filtered(lambda t: t.state == 'cancelled'):
            transaksi.state = 'draft'

    @api.depends('name', 'anggota_id.name', 'jenis_simpanan_id.name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} - {record.anggota_id.name} - {record.jenis_simpanan_id.name}"

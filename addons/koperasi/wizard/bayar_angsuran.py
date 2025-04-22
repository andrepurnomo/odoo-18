# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from odoo.tools import SQL


class KoperasiBayarAngsuran(models.TransientModel):
    _name = 'koperasi.wizard.bayar.angsuran'
    _description = 'Wizard Bayar Angsuran'

    angsuran_id = fields.Many2one(
        'koperasi.angsuran.pinjaman', string='Angsuran', required=True)
    anggota_id = fields.Many2one(
        related='angsuran_id.anggota_id', string='Anggota', readonly=True)
    pinjaman_id = fields.Many2one(
        related='angsuran_id.pinjaman_id', string='Pinjaman', readonly=True)
    tanggal_jatuh_tempo = fields.Date(
        related='angsuran_id.tanggal_jatuh_tempo', string='Tanggal Jatuh Tempo', readonly=True)
    total_angsuran = fields.Monetary(related='angsuran_id.total_angsuran_bulan',
                                     string='Total Angsuran', readonly=True, currency_field='currency_id')
    tanggal_pembayaran = fields.Date(
        string='Tanggal Pembayaran', required=True, default=fields.Date.today)
    jumlah_dibayar = fields.Monetary(
        string='Jumlah Dibayar', required=True, currency_field='currency_id')
    denda = fields.Monetary(string='Denda', default=0.0,
                            currency_field='currency_id')
    metode_pembayaran = fields.Selection([
        ('tunai', 'Tunai'),
        ('transfer', 'Transfer'),
        ('potong_simpanan', 'Potong Simpanan Sukarela')
    ], string='Metode Pembayaran', required=True, default='tunai')
    keterangan = fields.Text(string='Keterangan')
    simpanan_sukarela_id = fields.Many2one('koperasi.simpanan', string='Simpanan Sukarela',
                                           domain="[('anggota_id', '=', anggota_id), ('jenis_simpanan_id.kode', '=', 'sukarela')]")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.onchange('angsuran_id')
    def _onchange_angsuran_id(self):
        if self.angsuran_id:
            self.jumlah_dibayar = self.total_angsuran

            # Hitung denda jika telat
            if self.tanggal_pembayaran > self.tanggal_jatuh_tempo:
                # Contoh perhitungan denda: 0.5% dari total angsuran per hari keterlambatan
                days_late = (self.tanggal_pembayaran -
                             self.tanggal_jatuh_tempo).days
                self.denda = self.total_angsuran * 0.005 * days_late

    @api.onchange('tanggal_pembayaran')
    def _onchange_tanggal_pembayaran(self):
        if self.tanggal_pembayaran and self.tanggal_jatuh_tempo and self.total_angsuran:
            if self.tanggal_pembayaran > self.tanggal_jatuh_tempo:
                days_late = (self.tanggal_pembayaran -
                             self.tanggal_jatuh_tempo).days
                self.denda = self.total_angsuran * 0.005 * days_late
            else:
                self.denda = 0.0

    @api.constrains('jumlah_dibayar', 'metode_pembayaran', 'simpanan_sukarela_id')
    def _check_payment(self):
        for wizard in self:
            if wizard.jumlah_dibayar <= 0:
                raise ValidationError(
                    _('Jumlah pembayaran harus lebih dari 0.'))

            if wizard.metode_pembayaran == 'potong_simpanan':
                if not wizard.simpanan_sukarela_id:
                    raise ValidationError(
                        _('Simpanan Sukarela harus dipilih untuk metode potong simpanan.'))

                if wizard.simpanan_sukarela_id.saldo < wizard.jumlah_dibayar:
                    raise ValidationError(
                        _('Saldo Simpanan Sukarela tidak cukup.'))

    def action_bayar(self):
        self.ensure_one()

        if self.angsuran_id.status_pembayaran == 'sudah_bayar':
            raise ValidationError(_('Angsuran ini sudah dibayar.'))

        # Proses pembayaran berdasarkan metode
        if self.metode_pembayaran == 'potong_simpanan':
            # Buat transaksi penarikan simpanan
            transaksi_vals = {
                'anggota_id': self.anggota_id.id,
                'jenis_simpanan_id': self.simpanan_sukarela_id.jenis_simpanan_id.id,
                'tipe_transaksi': 'tarik',
                'jumlah': self.jumlah_dibayar,
                'tanggal_transaksi': self.tanggal_pembayaran,
                'keterangan': f'Pembayaran angsuran ke-{self.angsuran_id.angsuran_ke} untuk pinjaman {self.pinjaman_id.name}',
            }
            transaksi = self.env['koperasi.transaksi.simpanan'].create(
                transaksi_vals)
            transaksi.action_confirm()

        # Update data angsuran
        self.angsuran_id.write({
            'tanggal_pembayaran': self.tanggal_pembayaran,
            'jumlah_dibayar': self.jumlah_dibayar,
            'denda': self.denda,
            'status_pembayaran': 'telat_bayar' if self.tanggal_pembayaran > self.tanggal_jatuh_tempo else 'sudah_bayar',
            'keterangan': self.keterangan,
        })

        # Update status pinjaman jika perlu
        self.pinjaman_id.action_check_status()

        return {'type': 'ir.actions.act_window_close'}

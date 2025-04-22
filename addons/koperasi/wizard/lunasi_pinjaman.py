# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class KoperasiLunasiPinjaman(models.TransientModel):
    _name = 'koperasi.wizard.lunasi.pinjaman'
    _description = 'Wizard Lunasi Pinjaman'

    pinjaman_id = fields.Many2one(
        'koperasi.pinjaman', string='Pinjaman', required=True)
    sisa_pinjaman = fields.Monetary(related='pinjaman_id.sisa_pinjaman', string='Sisa Pinjaman',
                                    readonly=True, currency_field='currency_id')
    tanggal_pelunasan = fields.Date(
        string='Tanggal Pelunasan', required=True, default=fields.Date.today)
    metode_pembayaran = fields.Selection([
        ('tunai', 'Tunai'),
        ('transfer', 'Transfer'),
        ('potong_simpanan', 'Potong Simpanan Sukarela')
    ], string='Metode Pembayaran', required=True, default='tunai')
    anggota_id = fields.Many2one(
        related='pinjaman_id.anggota_id', string='Anggota', readonly=True)
    simpanan_sukarela_id = fields.Many2one('koperasi.simpanan', string='Simpanan Sukarela',
                                           domain="[('anggota_id', '=', anggota_id), ('jenis_simpanan_id.kode', '=', 'sukarela')]")
    keterangan = fields.Text(string='Keterangan')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.constrains('metode_pembayaran', 'simpanan_sukarela_id')
    def _check_metode_pembayaran(self):
        for wizard in self:
            if wizard.metode_pembayaran == 'potong_simpanan':
                if not wizard.simpanan_sukarela_id:
                    raise ValidationError(
                        _('Simpanan Sukarela harus dipilih untuk metode potong simpanan.'))

                if wizard.simpanan_sukarela_id.saldo < wizard.sisa_pinjaman:
                    raise ValidationError(
                        _('Saldo Simpanan Sukarela tidak cukup untuk pelunasan.'))

    def action_lunasi(self):
        self.ensure_one()

        if self.pinjaman_id.status_pinjaman not in ['aktif', 'menunggak']:
            raise ValidationError(
                _('Hanya pinjaman aktif atau menunggak yang dapat dilunasi.'))

        # Proses pelunasan berdasarkan metode pembayaran
        if self.metode_pembayaran == 'potong_simpanan':
            # Buat transaksi penarikan simpanan
            transaksi_vals = {
                'anggota_id': self.anggota_id.id,
                'jenis_simpanan_id': self.simpanan_sukarela_id.jenis_simpanan_id.id,
                'tipe_transaksi': 'tarik',
                'jumlah': self.sisa_pinjaman,
                'tanggal_transaksi': self.tanggal_pelunasan,
                'keterangan': f'Pelunasan pinjaman {self.pinjaman_id.name}',
            }
            transaksi = self.env['koperasi.transaksi.simpanan'].create(
                transaksi_vals)
            transaksi.action_confirm()

        # Tandai semua angsuran yang belum dibayar sebagai sudah dibayar
        angsuran_belum_bayar = self.pinjaman_id.angsuran_ids.filtered(
            lambda a: a.status_pembayaran == 'belum_bayar')
        for angsuran in angsuran_belum_bayar:
            angsuran.write({
                'tanggal_pembayaran': self.tanggal_pelunasan,
                'jumlah_dibayar': angsuran.total_angsuran_bulan,
                'status_pembayaran': 'sudah_bayar',
                'keterangan': 'Pelunasan dipercepat: ' + (self.keterangan or ''),
            })

        # Update status pinjaman menjadi lunas
        self.pinjaman_id.write({
            'status_pinjaman': 'lunas',
            'keterangan': (self.pinjaman_id.keterangan or '') + '\nDilunasi pada ' + str(self.tanggal_pelunasan) + ': ' + (self.keterangan or ''),
        })

        return {'type': 'ir.actions.act_window_close'}

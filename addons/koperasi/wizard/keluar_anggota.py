# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class KoperasiKeluarAnggota(models.TransientModel):
    _name = 'koperasi.wizard.keluar.anggota'
    _description = 'Wizard Keluar Anggota'

    anggota_id = fields.Many2one(
        'koperasi.anggota', string='Anggota', required=True)
    tanggal_keluar = fields.Date(
        string='Tanggal Keluar', required=True, default=fields.Date.today)
    alasan_keluar = fields.Text(string='Alasan Keluar')

    total_simpanan_pokok = fields.Monetary(related='anggota_id.total_simpanan_pokok', string='Total Simpanan Pokok',
                                           readonly=True, currency_field='currency_id')
    total_simpanan_wajib = fields.Monetary(related='anggota_id.total_simpanan_wajib', string='Total Simpanan Wajib',
                                           readonly=True, currency_field='currency_id')
    total_simpanan_sukarela = fields.Monetary(related='anggota_id.total_simpanan_sukarela', string='Total Simpanan Sukarela',
                                              readonly=True, currency_field='currency_id')
    total_pengembalian = fields.Monetary(compute='_compute_total_pengembalian', string='Total Pengembalian',
                                         currency_field='currency_id', precompute=True)

    has_active_loans = fields.Boolean(
        compute='_compute_has_active_loans', string='Memiliki Pinjaman Aktif', precompute=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('anggota_id', 'total_simpanan_pokok', 'total_simpanan_wajib', 'total_simpanan_sukarela')
    def _compute_total_pengembalian(self):
        for wizard in self:
            wizard.total_pengembalian = wizard.total_simpanan_pokok + \
                wizard.total_simpanan_wajib + wizard.total_simpanan_sukarela

    @api.depends('anggota_id')
    def _compute_has_active_loans(self):
        for wizard in self:
            active_loans = self.env['koperasi.pinjaman'].search_count([
                ('anggota_id', '=', wizard.anggota_id.id),
                ('status_pinjaman', 'in', ['aktif', 'menunggak'])
            ])
            wizard.has_active_loans = active_loans > 0

    def action_keluar(self):
        self.ensure_one()

        if self.has_active_loans:
            raise ValidationError(
                _('Anggota masih memiliki pinjaman aktif. Harap lunasi semua pinjaman terlebih dahulu.'))

        # Proses pengembalian simpanan
        if self.total_pengembalian > 0:
            # Transaksi pengembalian simpanan pokok
            if self.total_simpanan_pokok > 0:
                pokok_id = self.env['koperasi.jenis.simpanan'].search(
                    [('kode', '=', 'pokok')], limit=1)
                if pokok_id:
                    transaksi_vals = {
                        'anggota_id': self.anggota_id.id,
                        'jenis_simpanan_id': pokok_id.id,
                        'tipe_transaksi': 'pengembalian_keluar',
                        'jumlah': self.total_simpanan_pokok,
                        'tanggal_transaksi': self.tanggal_keluar,
                        'keterangan': f'Pengembalian Simpanan Pokok karena keluar dari keanggotaan: {self.alasan_keluar or ""}',
                    }
                    transaksi = self.env['koperasi.transaksi.simpanan'].create(
                        transaksi_vals)
                    transaksi.action_confirm()

            # Transaksi pengembalian simpanan wajib
            if self.total_simpanan_wajib > 0:
                wajib_id = self.env['koperasi.jenis.simpanan'].search(
                    [('kode', '=', 'wajib')], limit=1)
                if wajib_id:
                    transaksi_vals = {
                        'anggota_id': self.anggota_id.id,
                        'jenis_simpanan_id': wajib_id.id,
                        'tipe_transaksi': 'pengembalian_keluar',
                        'jumlah': self.total_simpanan_wajib,
                        'tanggal_transaksi': self.tanggal_keluar,
                        'keterangan': f'Pengembalian Simpanan Wajib karena keluar dari keanggotaan: {self.alasan_keluar or ""}',
                    }
                    transaksi = self.env['koperasi.transaksi.simpanan'].create(
                        transaksi_vals)
                    transaksi.action_confirm()

            # Transaksi pengembalian simpanan sukarela
            if self.total_simpanan_sukarela > 0:
                sukarela_id = self.env['koperasi.jenis.simpanan'].search(
                    [('kode', '=', 'sukarela')], limit=1)
                if sukarela_id:
                    transaksi_vals = {
                        'anggota_id': self.anggota_id.id,
                        'jenis_simpanan_id': sukarela_id.id,
                        'tipe_transaksi': 'pengembalian_keluar',
                        'jumlah': self.total_simpanan_sukarela,
                        'tanggal_transaksi': self.tanggal_keluar,
                        'keterangan': f'Pengembalian Simpanan Sukarela karena keluar dari keanggotaan: {self.alasan_keluar or ""}',
                    }
                    transaksi = self.env['koperasi.transaksi.simpanan'].create(
                        transaksi_vals)
                    transaksi.action_confirm()

        # Update status anggota
        self.anggota_id.write({
            'status_keanggotaan': 'non_aktif',
            'tanggal_keluar': self.tanggal_keluar,
        })

        return {'type': 'ir.actions.act_window_close'}

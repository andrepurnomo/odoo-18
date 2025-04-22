# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
from odoo.tools import SQL


class KoperasiHitungSHU(models.TransientModel):
    _name = 'koperasi.wizard.hitung.shu'
    _description = 'Wizard Hitung SHU'

    tahun_buku = fields.Integer(
        string='Tahun Buku', required=True, default=lambda self: date.today().year)
    total_pendapatan_bunga_diterima = fields.Monetary(
        string='Total Pendapatan Bunga Diterima', readonly=True, currency_field='currency_id')
    total_pendapatan_bunga_akan_masuk = fields.Monetary(
        string='Total Pendapatan Bunga Akan Masuk', readonly=True, currency_field='currency_id')
    total_pendapatan_bunga = fields.Monetary(
        string='Total Pendapatan Bunga', readonly=True, compute='_compute_total_pendapatan',
        currency_field='currency_id', precompute=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('total_pendapatan_bunga_diterima', 'total_pendapatan_bunga_akan_masuk')
    def _compute_total_pendapatan(self):
        for wizard in self:
            wizard.total_pendapatan_bunga = wizard.total_pendapatan_bunga_diterima + \
                wizard.total_pendapatan_bunga_akan_masuk

    @api.onchange('tahun_buku')
    def _onchange_tahun_buku(self):
        if self.tahun_buku:
            # Hitung total pendapatan bunga yang sudah diterima
            start_date = date(self.tahun_buku, 1, 1)
            end_date = date(self.tahun_buku, 12, 31)

            # Pendapatan bunga yang sudah diterima
            angsuran_dibayar = self.env['koperasi.angsuran.pinjaman'].search([
                ('status_pembayaran', '=', 'sudah_bayar'),
                ('tanggal_pembayaran', '>=', start_date),
                ('tanggal_pembayaran', '<=', end_date)
            ])
            self.total_pendapatan_bunga_diterima = sum(
                angsuran_dibayar.mapped('jumlah_bunga_angsuran'))

            # Pendapatan bunga yang akan diterima (jatuh tempo di tahun buku tapi belum dibayar)
            angsuran_akan_masuk = self.env['koperasi.angsuran.pinjaman'].search([
                ('status_pembayaran', '=', 'belum_bayar'),
                ('tanggal_jatuh_tempo', '>=', start_date),
                ('tanggal_jatuh_tempo', '<=', end_date)
            ])
            self.total_pendapatan_bunga_akan_masuk = sum(
                angsuran_akan_masuk.mapped('jumlah_bunga_angsuran'))

    def action_print_laporan_shu(self):
        self.ensure_one()
        return {
            'name': _('Laporan SHU'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.laporan.shu',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_tahun_buku': self.tahun_buku,
                'default_total_pendapatan_bunga_diterima': self.total_pendapatan_bunga_diterima,
                'default_total_pendapatan_bunga_akan_masuk': self.total_pendapatan_bunga_akan_masuk,
            }
        }

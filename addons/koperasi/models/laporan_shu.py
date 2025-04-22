# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class KoperasiLaporanShu(models.Model):
    _name = 'koperasi.laporan.shu'
    _description = 'Laporan SHU Koperasi'

    tahun_buku = fields.Integer(string='Tahun Buku', required=True)
    total_pendapatan_bunga_diterima = fields.Monetary(
        string='Total Pendapatan Bunga Diterima', currency_field='currency_id')
    total_pendapatan_bunga_akan_masuk = fields.Monetary(
        string='Total Pendapatan Bunga Akan Masuk', currency_field='currency_id')
    total_pendapatan_bunga = fields.Monetary(
        string='Total Pendapatan Bunga', compute='_compute_total_pendapatan',
        currency_field='currency_id', store=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    @api.depends('total_pendapatan_bunga_diterima', 'total_pendapatan_bunga_akan_masuk')
    def _compute_total_pendapatan(self):
        for record in self:
            record.total_pendapatan_bunga = record.total_pendapatan_bunga_diterima + record.total_pendapatan_bunga_akan_masuk
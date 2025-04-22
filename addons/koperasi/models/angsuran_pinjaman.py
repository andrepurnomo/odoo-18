# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class KoperasiAngsuranPinjaman(models.Model):
    _name = 'koperasi.angsuran.pinjaman'
    _description = 'Angsuran Pinjaman Koperasi'
    _order = 'pinjaman_id, angsuran_ke'
    _check_company_auto = True

    pinjaman_id = fields.Many2one(
        'koperasi.pinjaman', string='Pinjaman', required=True, ondelete='cascade')
    anggota_id = fields.Many2one(
        related='pinjaman_id.anggota_id', string='Anggota', store=True)
    angsuran_ke = fields.Integer(string='Angsuran Ke', required=True)
    jumlah_pokok_angsuran = fields.Monetary(
        string='Pokok Angsuran', required=True, currency_field='currency_id')
    jumlah_bunga_angsuran = fields.Monetary(
        string='Bunga Angsuran', required=True, currency_field='currency_id')
    total_angsuran_bulan = fields.Monetary(string='Total Angsuran', compute='_compute_total_angsuran',
                                           store=True, precompute=True, currency_field='currency_id')
    tanggal_jatuh_tempo = fields.Date(
        string='Tanggal Jatuh Tempo', required=True)
    tanggal_pembayaran = fields.Date(string='Tanggal Pembayaran')
    jumlah_dibayar = fields.Monetary(
        string='Jumlah Dibayar', currency_field='currency_id')
    denda = fields.Monetary(string='Denda', default=0.0,
                            currency_field='currency_id')
    status_pembayaran = fields.Selection([
        ('belum_bayar', 'Belum Bayar'),
        ('sudah_bayar', 'Sudah Bayar'),
        ('telat_bayar', 'Telat Bayar')
    ], string='Status Pembayaran', default='belum_bayar', required=True)
    keterangan = fields.Text(string='Keterangan')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('jumlah_pokok_angsuran', 'jumlah_bunga_angsuran', 'denda')
    def _compute_total_angsuran(self):
        for angsuran in self:
            angsuran.total_angsuran_bulan = angsuran.jumlah_pokok_angsuran + \
                angsuran.jumlah_bunga_angsuran + angsuran.denda

    def action_bayar_angsuran(self):
        self.ensure_one()
        return {
            'name': _('Bayar Angsuran'),
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.wizard.bayar.angsuran',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_angsuran_id': self.id}
        }

    def action_reset(self):
        for angsuran in self.filtered(lambda a: a.status_pembayaran == 'sudah_bayar'):
            angsuran.write({
                'status_pembayaran': 'belum_bayar',
                'tanggal_pembayaran': False,
                'jumlah_dibayar': 0,
                'keterangan': f"{angsuran.keterangan or ''}\nPembayaran dibatalkan pada {fields.Date.today()}"
            })
            # Update status pinjaman jika perlu
            if angsuran.pinjaman_id.status_pinjaman == 'lunas':
                angsuran.pinjaman_id.status_pinjaman = 'aktif'

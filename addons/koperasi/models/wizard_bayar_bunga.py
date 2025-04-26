# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class KoperasiWizardBayarBunga(models.TransientModel):
    _name = 'koperasi.wizard.bayar.bunga'
    _description = 'Wizard Pembayaran Bunga Simpanan'

    tanggal_transaksi = fields.Date(
        string='Tanggal Transaksi', required=True, default=fields.Date.today)
    bulan = fields.Selection([
        ('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret'), ('04', 'April'),
        ('05', 'Mei'), ('06', 'Juni'), ('07', 'Juli'), ('08', 'Agustus'),
        ('09', 'September'), ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember')
    ], string='Bulan', required=True, default=lambda self: str(fields.Date.today().month).zfill(2))
    tahun = fields.Integer(string='Tahun', required=True,
                           default=lambda self: fields.Date.today().year)

    jenis_simpanan_id = fields.Many2one('koperasi.jenis.simpanan', string='Jenis Simpanan', required=True,
                                        domain=[('kode', '=', 'sukarela')])

    suku_bunga = fields.Float(
        string='Suku Bunga Tahunan (%)', required=True, default=3.0)
    keterangan = fields.Text(
        string='Keterangan', default='Pembayaran bunga simpanan bulanan')

    line_ids = fields.One2many(
        'koperasi.wizard.bayar.bunga.line', 'wizard_id', string='Detail Bunga Anggota')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    def generate_bunga_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        # Calculate the last day of the selected month
        first_day = date(self.tahun, int(self.bulan), 1)
        if int(self.bulan) == 12:
            last_day = date(self.tahun + 1, 1, 1) - relativedelta(days=1)
        else:
            last_day = date(self.tahun, int(self.bulan) +
                            1, 1) - relativedelta(days=1)

        # Find all members with sukarela savings
        simpanan_sukarela = self.env['koperasi.simpanan'].search([
            ('jenis_simpanan_id', '=', self.jenis_simpanan_id.id),
            ('saldo', '>', 0)
        ])

        lines = []
        for simpanan in simpanan_sukarela:
            # Calculate monthly interest (annual interest / 12)
            bunga_bulanan = simpanan.saldo * (self.suku_bunga / 100 / 12)

            # Create line
            line_vals = {
                'wizard_id': self.id,
                'anggota_id': simpanan.anggota_id.id,
                'saldo_simpanan': simpanan.saldo,
                'bunga_bulanan': bunga_bulanan,
                # Flag if taxable (>240,000)
                'kena_pajak': bunga_bulanan > 240000,
            }

            if bunga_bulanan > 240000:
                line_vals['jumlah_pajak'] = bunga_bulanan * 0.1  # 10% tax

            lines.append(line_vals)

        # Create lines
        self.env['koperasi.wizard.bayar.bunga.line'].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'koperasi.wizard.bayar.bunga',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def process_bunga_payments(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(
                _('Tidak ada data bunga simpanan untuk diproses.'))

        # Create transactions for each line
        for line in self.line_ids:
            if line.include_payment and line.bunga_bulanan > 0:  # Only process positive interest amounts
                vals = {
                    'anggota_id': line.anggota_id.id,  # Correctly use anggota_id from the line
                    'jenis_simpanan_id': self.jenis_simpanan_id.id,
                    'tipe_transaksi': 'bunga_simpanan',
                    'jumlah': line.bunga_bulanan,
                    'tanggal_transaksi': self.tanggal_transaksi,
                    'keterangan': self.keterangan,
                    'bunga_kena_pajak': line.kena_pajak,
                    'jumlah_pajak': line.jumlah_pajak,
                }

                transaksi = self.env['koperasi.transaksi.simpanan'].create(
                    vals)
                transaksi.action_confirm()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sukses'),
                'message': _('Pembayaran bunga simpanan berhasil diproses.'),
                'type': 'success',
                'sticky': False,
            }
        }


class KoperasiWizardBayarBungaLine(models.TransientModel):
    _name = 'koperasi.wizard.bayar.bunga.line'
    _description = 'Detail Bunga Simpanan Per Anggota'

    wizard_id = fields.Many2one('koperasi.wizard.bayar.bunga', string='Wizard')
    anggota_id = fields.Many2one(
        'koperasi.anggota', string='Anggota', required=True)
    saldo_simpanan = fields.Monetary(
        string='Saldo Simpanan', currency_field='currency_id')
    bunga_bulanan = fields.Monetary(
        string='Bunga Bulanan', currency_field='currency_id')
    kena_pajak = fields.Boolean(string='Kena Pajak', default=False)
    jumlah_pajak = fields.Monetary(
        string='Pajak (10%)', currency_field='currency_id', default=0.0)
    jumlah_setelah_pajak = fields.Monetary(string='Jumlah Setelah Pajak', compute='_compute_setelah_pajak',
                                           currency_field='currency_id')

    include_payment = fields.Boolean(string='Proses Pembayaran', default=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('bunga_bulanan', 'jumlah_pajak', 'kena_pajak')
    def _compute_setelah_pajak(self):
        for line in self:
            if line.kena_pajak:
                line.jumlah_setelah_pajak = line.bunga_bulanan - line.jumlah_pajak
            else:
                line.jumlah_setelah_pajak = line.bunga_bulanan

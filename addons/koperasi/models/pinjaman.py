# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import SQL


class KoperasiPinjaman(models.Model):
    _name = 'koperasi.pinjaman'
    _description = 'Pinjaman Koperasi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tanggal_pengajuan desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Kode Pinjaman', required=True,
                       copy=False, readonly=True, default=lambda self: _('New'))
    anggota_id = fields.Many2one(
        'koperasi.anggota', string='Anggota', required=True, tracking=True)
    jumlah_pokok = fields.Monetary(
        string='Jumlah Pokok', required=True, currency_field='currency_id', tracking=True)
    tenor_bulan = fields.Integer(
        string='Tenor (Bulan)', required=True, tracking=True)
    bunga_per_bulan = fields.Float(
        string='Bunga per Bulan (%)', default=0.9, required=True, tracking=True)
    total_bunga = fields.Monetary(string='Total Bunga', compute='_compute_pinjaman_details',
                                  store=True, precompute=True, currency_field='currency_id')
    total_pinjaman = fields.Monetary(string='Total Pinjaman', compute='_compute_pinjaman_details',
                                     store=True, precompute=True, currency_field='currency_id')
    angsuran_per_bulan = fields.Monetary(string='Angsuran per Bulan', compute='_compute_pinjaman_details',
                                         store=True, precompute=True, currency_field='currency_id')
    sisa_pinjaman = fields.Monetary(string='Sisa Pinjaman', compute='_compute_sisa_pinjaman',
                                    store=True, precompute=True, currency_field='currency_id')
    tanggal_pengajuan = fields.Date(
        string='Tanggal Pengajuan', default=fields.Date.today, required=True, tracking=True)
    tanggal_persetujuan = fields.Date(
        string='Tanggal Persetujuan', tracking=True)
    tanggal_mulai_angsuran = fields.Date(
        string='Tanggal Mulai Angsuran', tracking=True)
    tanggal_jatuh_tempo_lunas = fields.Date(string='Tanggal Jatuh Tempo Lunas', compute='_compute_pinjaman_details',
                                            store=True, precompute=True)
    status_pinjaman = fields.Selection([
        ('pengajuan', 'Pengajuan'),
        ('disetujui', 'Disetujui'),
        ('ditolak', 'Ditolak'),
        ('aktif', 'Aktif'),
        ('lunas', 'Lunas'),
        ('menunggak', 'Menunggak')
    ], string='Status Pinjaman', default='pengajuan', required=True, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    alasan_penolakan = fields.Text(string='Alasan Penolakan', tracking=True)

    angsuran_ids = fields.One2many(
        'koperasi.angsuran.pinjaman', 'pinjaman_id', string='Angsuran')
    total_dibayar = fields.Monetary(string='Total Dibayar', compute='_compute_sisa_pinjaman',
                                    store=True, precompute=True, currency_field='currency_id')
    angsuran_dibayar = fields.Integer(string='Angsuran Dibayar', compute='_compute_sisa_pinjaman',
                                      store=True, precompute=True)
    angsuran_tersisa = fields.Integer(string='Angsuran Tersisa', compute='_compute_sisa_pinjaman',
                                      store=True, precompute=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'koperasi.pinjaman') or _('New')
        return super().create(vals_list)

    @api.depends('jumlah_pokok', 'tenor_bulan', 'bunga_per_bulan', 'tanggal_mulai_angsuran')
    def _compute_pinjaman_details(self):
        for pinjaman in self:
            pinjaman.total_bunga = pinjaman.jumlah_pokok * \
                (pinjaman.bunga_per_bulan / 100) * pinjaman.tenor_bulan
            pinjaman.total_pinjaman = pinjaman.jumlah_pokok + pinjaman.total_bunga
            pinjaman.angsuran_per_bulan = pinjaman.total_pinjaman / \
                pinjaman.tenor_bulan if pinjaman.tenor_bulan else 0

            if pinjaman.tanggal_mulai_angsuran:
                pinjaman.tanggal_jatuh_tempo_lunas = pinjaman.tanggal_mulai_angsuran + \
                    relativedelta(months=pinjaman.tenor_bulan)

    @api.depends('angsuran_ids.jumlah_dibayar', 'angsuran_ids.status_pembayaran', 'total_pinjaman')
    def _compute_sisa_pinjaman(self):
        for pinjaman in self:
            angsuran_dibayar = pinjaman.angsuran_ids.filtered(
                lambda a: a.status_pembayaran == 'sudah_bayar')
            pinjaman.total_dibayar = sum(
                angsuran_dibayar.mapped('jumlah_dibayar'))
            pinjaman.sisa_pinjaman = pinjaman.total_pinjaman - pinjaman.total_dibayar
            pinjaman.angsuran_dibayar = len(angsuran_dibayar)
            pinjaman.angsuran_tersisa = pinjaman.tenor_bulan - pinjaman.angsuran_dibayar

    @api.constrains('jumlah_pokok', 'tenor_bulan', 'bunga_per_bulan')
    def _check_pinjaman_details(self):
        for pinjaman in self:
            if pinjaman.jumlah_pokok <= 0:
                raise ValidationError(
                    _('Jumlah pokok pinjaman harus lebih dari 0.'))
            if pinjaman.tenor_bulan <= 0:
                raise ValidationError(
                    _('Tenor pinjaman harus lebih dari 0 bulan.'))
            if pinjaman.bunga_per_bulan < 0:
                raise ValidationError(_('Bunga pinjaman tidak boleh negatif.'))

    def action_approve(self):
        for pinjaman in self.filtered(lambda p: p.status_pinjaman == 'pengajuan'):
            pinjaman.write({
                'status_pinjaman': 'disetujui',
                'tanggal_persetujuan': fields.Date.today(),
            })
            # Tampilkan wizard untuk mengatur tanggal mulai angsuran
            return {
                'name': _('Set Tanggal Mulai Angsuran'),
                'type': 'ir.actions.act_window',
                'res_model': 'koperasi.wizard.mulai.angsuran',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_pinjaman_id': pinjaman.id}
            }

    def action_reject(self):
        for pinjaman in self.filtered(lambda p: p.status_pinjaman == 'pengajuan'):
            return {
                'name': _('Tolak Pinjaman'),
                'type': 'ir.actions.act_window',
                'res_model': 'koperasi.wizard.tolak.pinjaman',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_pinjaman_id': pinjaman.id}
            }

    def action_activate(self):
        for pinjaman in self.filtered(lambda p: p.status_pinjaman == 'disetujui'):
            if not pinjaman.tanggal_mulai_angsuran:
                raise ValidationError(
                    _('Tanggal mulai angsuran harus diisi terlebih dahulu.'))

            pinjaman.status_pinjaman = 'aktif'

            # Buat jadwal angsuran
            angsuran_vals = []
            tanggal_jatuh_tempo = pinjaman.tanggal_mulai_angsuran
            jumlah_pokok_per_bulan = pinjaman.jumlah_pokok / pinjaman.tenor_bulan
            jumlah_bunga_per_bulan = pinjaman.jumlah_pokok * \
                (pinjaman.bunga_per_bulan / 100)

            for i in range(1, pinjaman.tenor_bulan + 1):
                angsuran_vals.append({
                    'pinjaman_id': pinjaman.id,
                    'angsuran_ke': i,
                    'jumlah_pokok_angsuran': jumlah_pokok_per_bulan,
                    'jumlah_bunga_angsuran': jumlah_bunga_per_bulan,
                    'total_angsuran_bulan': jumlah_pokok_per_bulan + jumlah_bunga_per_bulan,
                    'tanggal_jatuh_tempo': tanggal_jatuh_tempo,
                })
                tanggal_jatuh_tempo = tanggal_jatuh_tempo + \
                    relativedelta(months=1)

            # Buat angsuran
            self.env['koperasi.angsuran.pinjaman'].create(angsuran_vals)

    def action_set_lunas(self):
        for pinjaman in self:
            # Jika semua angsuran sudah dibayar, set status ke lunas
            if all(angsuran.status_pembayaran == 'sudah_bayar' for angsuran in pinjaman.angsuran_ids):
                pinjaman.status_pinjaman = 'lunas'
            else:
                return {
                    'name': _('Pelunasan Pinjaman'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'koperasi.wizard.lunasi.pinjaman',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_pinjaman_id': pinjaman.id}
                }

    def action_check_status(self):
        today = fields.Date.today()
        for pinjaman in self.search([('status_pinjaman', 'in', ['aktif', 'menunggak'])]):
            # Cek apakah ada angsuran yang sudah jatuh tempo tapi belum dibayar
            angsuran_telat = pinjaman.angsuran_ids.filtered(
                lambda a: a.tanggal_jatuh_tempo < today and a.status_pembayaran == 'belum_bayar'
            )

            if angsuran_telat:
                pinjaman.status_pinjaman = 'menunggak'
            else:
                pinjaman.status_pinjaman = 'aktif'

            # Cek apakah pinjaman sudah lunas
            if all(angsuran.status_pembayaran == 'sudah_bayar' for angsuran in pinjaman.angsuran_ids):
                pinjaman.status_pinjaman = 'lunas'

    @api.depends('name', 'anggota_id.name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} - {record.anggota_id.name}" if record.anggota_id else record.name

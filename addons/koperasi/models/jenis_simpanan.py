# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import SQL


class KoperasiJenisSimpanan(models.Model):
    _name = 'koperasi.jenis.simpanan'
    _description = 'Jenis Simpanan Koperasi'
    _order = 'name'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Nama Simpanan', required=True,
                       index='trigram', translate=True)
    kode = fields.Char(string='Kode', required=True)
    deskripsi = fields.Text(string='Deskripsi')
    is_required = fields.Boolean(string='Wajib', default=False,
                                 help='Jika dicentang, jenis simpanan ini wajib untuk semua anggota')
    min_amount = fields.Monetary(
        string='Jumlah Minimal', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    _sql_constraints = [
        ('kode_unique', 'UNIQUE(kode)', 'Kode jenis simpanan harus unik!')
    ]

    @api.depends('name', 'kode')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.kode}] {record.name}" if record.kode else record.name

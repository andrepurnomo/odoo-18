# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import SQL


class KoperasiSimpanan(models.Model):
    _name = 'koperasi.simpanan'
    _description = 'Simpanan Anggota Koperasi'
    _check_company_auto = True

    anggota_id = fields.Many2one(
        'koperasi.anggota', string='Anggota', required=True, ondelete='cascade')
    jenis_simpanan_id = fields.Many2one(
        'koperasi.jenis.simpanan', string='Jenis Simpanan', required=True)
    saldo = fields.Monetary(
        string='Saldo', currency_field='currency_id', default=0.0)
    last_update = fields.Datetime(
        string='Terakhir Diperbarui', default=fields.Datetime.now)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    company_id = fields.Many2one("res.company", string="Company",
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('anggota_jenis_simpanan_unique', 'UNIQUE(anggota_id, jenis_simpanan_id)',
         'Setiap anggota hanya boleh memiliki satu saldo per jenis simpanan!')
    ]

    def name_get(self):
        result = []
        for simpanan in self:
            name = f"{simpanan.anggota_id.name} - {simpanan.jenis_simpanan_id.name}"
            result.append((simpanan.id, name))
        return result

    def action_lihat_transaksi(self):
        return {
            'name': _('Transaksi Simpanan'),
            'view_mode': 'list,form',
            'res_model': 'koperasi.transaksi.simpanan',
            'domain': [
                ('anggota_id', '=', self.anggota_id.id),
                ('jenis_simpanan_id', '=', self.jenis_simpanan_id.id)
            ],
            'type': 'ir.actions.act_window',
            'context': {
                'default_anggota_id': self.anggota_id.id,
                'default_jenis_simpanan_id': self.jenis_simpanan_id.id
            }
        }

    @api.depends('anggota_id.name', 'jenis_simpanan_id.name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.anggota_id.name} - {record.jenis_simpanan_id.name}"

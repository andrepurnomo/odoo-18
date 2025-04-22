# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class KoperasiMulaiAngsuran(models.TransientModel):
    _name = 'koperasi.wizard.mulai.angsuran'
    _description = 'Wizard Mulai Angsuran'

    pinjaman_id = fields.Many2one(
        'koperasi.pinjaman', string='Pinjaman', required=True)
    tanggal_mulai_angsuran = fields.Date(
        string='Tanggal Mulai Angsuran', required=True, default=fields.Date.today)

    @api.constrains('tanggal_mulai_angsuran')
    def _check_tanggal_mulai(self):
        for wizard in self:
            if wizard.tanggal_mulai_angsuran < wizard.pinjaman_id.tanggal_persetujuan:
                raise ValidationError(
                    _('Tanggal mulai angsuran tidak boleh sebelum tanggal persetujuan.'))

    def action_set_mulai_angsuran(self):
        self.ensure_one()
        if self.pinjaman_id.status_pinjaman == 'disetujui':
            self.pinjaman_id.write({
                'tanggal_mulai_angsuran': self.tanggal_mulai_angsuran,
            })
            # Aktifkan pinjaman
            self.pinjaman_id.action_activate()
        return {'type': 'ir.actions.act_window_close'}

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import SQL


class KoperasiTolakPinjaman(models.TransientModel):
    _name = 'koperasi.wizard.tolak.pinjaman'
    _description = 'Wizard Tolak Pinjaman'

    pinjaman_id = fields.Many2one(
        'koperasi.pinjaman', string='Pinjaman', required=True)
    alasan_penolakan = fields.Text(string='Alasan Penolakan', required=True)

    def action_tolak(self):
        self.ensure_one()
        if self.pinjaman_id.status_pinjaman == 'pengajuan':
            self.pinjaman_id.write({
                'status_pinjaman': 'ditolak',
                'alasan_penolakan': self.alasan_penolakan,
            })
        return {'type': 'ir.actions.act_window_close'}

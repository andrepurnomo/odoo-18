# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import SQL
from datetime import date
from dateutil.relativedelta import relativedelta


class KoperasiWizardLaporanPajak(models.TransientModel):
    _name = "koperasi.wizard.laporan.pajak"
    _description = "Wizard Laporan Pajak Simpanan"
    _check_company_auto = True

    bulan = fields.Selection([
        ("01", "Januari"), ("02", "Februari"), ("03", "Maret"), ("04", "April"),
        ("05", "Mei"), ("06", "Juni"), ("07", "Juli"), ("08", "Agustus"),
        ("09", "September"), ("10", "Oktober"), ("11", "November"), ("12", "Desember")
    ], string="Bulan", required=True,
        default=lambda self: str(
            (fields.Date.today() - relativedelta(months=1)).month).zfill(2),
        help="Bulan pajak yang akan dilaporkan")

    tahun = fields.Integer(string="Tahun", required=True,
                           default=lambda self: fields.Date.today().year,
                           help="Tahun pajak yang akan dilaporkan")

    pajak_ids = fields.Many2many(
        "koperasi.pajak.simpanan", string="Data Pajak", compute="_compute_pajak_ids",
        check_company=True)

    total_bunga = fields.Monetary(
        string="Total Bunga", compute="_compute_summary", currency_field="currency_id")
    total_pajak = fields.Monetary(
        string="Total Pajak", compute="_compute_summary", currency_field="currency_id")

    tanggal_lapor = fields.Date(
        string="Tanggal Pelaporan", default=fields.Date.today, required=True)

    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one("res.company", string="Company",
                                 default=lambda self: self.env.company)

    @api.depends("bulan", "tahun")
    def _compute_pajak_ids(self):
        for wizard in self:
            domain = [
                ("bulan", "=", wizard.bulan),
                ("tahun", "=", wizard.tahun),
                ("status", "in", ["potong", "setor"]),
                ("company_id", "=", wizard.company_id.id)
            ]
            wizard.pajak_ids = self.env["koperasi.pajak.simpanan"].search(
                domain)

    @api.depends("pajak_ids")
    def _compute_summary(self):
        for wizard in self:
            wizard.total_bunga = sum(wizard.pajak_ids.mapped("total_bunga"))
            wizard.total_pajak = sum(wizard.pajak_ids.mapped("jumlah_pajak"))

    def action_lapor_pajak(self):
        self.ensure_one()
        if not self.pajak_ids:
            raise ValidationError(
                _("Tidak ada data pajak untuk bulan dan tahun yang dipilih."))

        # Update status to reported and set reporting date
        self.pajak_ids.write({
            "status": "lapor",
            "tanggal_lapor": self.tanggal_lapor
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sukses"),
                "message": _("Pajak bunga simpanan berhasil dilaporkan."),
                "type": "success",
                "sticky": False,
            }
        }

    def action_cetak_laporan(self):
        self.ensure_one()
        if not self.pajak_ids:
            raise ValidationError(
                _("Tidak ada data pajak untuk bulan dan tahun yang dipilih."))

        # This would typically return a report action
        return {
            "name": _("Laporan Pajak Bunga Simpanan"),
            "type": "ir.actions.act_window",
            "res_model": "koperasi.wizard.laporan.pajak",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

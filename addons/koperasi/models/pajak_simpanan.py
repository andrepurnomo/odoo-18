# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import SQL
from datetime import date
from dateutil.relativedelta import relativedelta


class KoperasiPajakSimpanan(models.Model):
    _name = "koperasi.pajak.simpanan"
    _description = "Pajak Simpanan Koperasi"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "tanggal_pemotongan desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Nomor Bukti Potong", required=True, copy=False, readonly=True,
                       default=lambda self: _("New"))
    anggota_id = fields.Many2one("koperasi.anggota", string="Anggota", required=True,
                                 tracking=True, check_company=True)
    bulan = fields.Selection([
        ("01", "Januari"), ("02", "Februari"), ("03", "Maret"), ("04", "April"),
        ("05", "Mei"), ("06", "Juni"), ("07", "Juli"), ("08", "Agustus"),
        ("09", "September"), ("10", "Oktober"), ("11", "November"), ("12", "Desember")
    ], string="Bulan", required=True, tracking=True)
    tahun = fields.Integer(string="Tahun", required=True,
                           default=lambda self: fields.Date.today().year, tracking=True)
    tanggal_pemotongan = fields.Date(string="Tanggal Pemotongan", required=True,
                                     default=fields.Date.today, tracking=True)
    tanggal_lapor = fields.Date(string="Tanggal Pelaporan", tracking=True)

    total_bunga = fields.Monetary(string="Total Bunga Simpanan", currency_field="currency_id",
                                  required=True, tracking=True)
    batas_bebas_pajak = fields.Monetary(string="Batas Bebas Pajak", currency_field="currency_id",
                                        default=240000, readonly=True,
                                        help="Batas bunga simpanan yang tidak dikenakan pajak (Rp240.000)")
    bunga_kena_pajak = fields.Monetary(string="Bunga Kena Pajak", currency_field="currency_id",
                                       compute="_compute_pajak", store=True, readonly=True)
    tarif_pajak = fields.Float(
        string="Tarif PPh Final (%)", default=10, readonly=True)
    jumlah_pajak = fields.Monetary(string="Jumlah Pajak", currency_field="currency_id",
                                   compute="_compute_pajak", store=True, readonly=True)

    status = fields.Selection([
        ("draft", "Draft"),
        ("potong", "Dipotong"),
        ("setor", "Disetor"),
        ("lapor", "Dilaporkan")
    ], string="Status", default="draft", tracking=True)

    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one("res.company", string="Company",
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "koperasi.pajak.simpanan") or _("New")
        return super().create(vals_list)

    @api.depends("total_bunga", "batas_bebas_pajak", "tarif_pajak")
    def _compute_pajak(self):
        for record in self:
            # Jika bunga simpanan kurang dari atau sama dengan Rp240.000, tidak kena pajak
            if record.total_bunga <= record.batas_bebas_pajak:
                record.bunga_kena_pajak = 0
                record.jumlah_pajak = 0
            else:
                # Jika bunga simpanan lebih dari Rp240.000, kena pajak 10% dari seluruh bunga
                record.bunga_kena_pajak = record.total_bunga
                record.jumlah_pajak = record.bunga_kena_pajak * \
                    (record.tarif_pajak / 100)

    def action_potong_pajak(self):
        for record in self.filtered(lambda r: r.status == "draft"):
            record.status = "potong"

    def action_setor_pajak(self):
        for record in self.filtered(lambda r: r.status == "potong"):
            record.status = "setor"

    def action_lapor_pajak(self):
        for record in self.filtered(lambda r: r.status == "setor"):
            record.status = "lapor"
            record.tanggal_lapor = fields.Date.today()

    def action_reset_to_draft(self):
        for record in self:
            record.status = "draft"

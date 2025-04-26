# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import SQL
from datetime import date
from dateutil.relativedelta import relativedelta


class KoperasiPajakKoperasi(models.Model):
    _name = "koperasi.pajak.koperasi"
    _description = "Pajak Badan Koperasi"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "tahun desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Nomor", required=True, copy=False, readonly=True,
                       default=lambda self: _("New"))
    tahun_pajak = fields.Integer(string="Tahun Pajak", required=True,
                                 default=lambda self: fields.Date.today().year,
                                 tracking=True)
    tanggal_lapor = fields.Date(string="Tanggal Pelaporan", tracking=True)

    # Income details
    pendapatan_bunga = fields.Monetary(string="Pendapatan Bunga", currency_field="currency_id",
                                       help="Pendapatan bunga dari pinjaman anggota")
    pendapatan_lainnya = fields.Monetary(string="Pendapatan Lainnya", currency_field="currency_id",
                                         help="Pendapatan dari sumber lainnya")
    total_pendapatan = fields.Monetary(string="Total Pendapatan", compute="_compute_totals",
                                       store=True, currency_field="currency_id")

    # Expense details
    biaya_operasional = fields.Monetary(string="Biaya Operasional", currency_field="currency_id",
                                        help="Biaya untuk operasional koperasi")
    biaya_bunga_simpanan = fields.Monetary(string="Biaya Bunga Simpanan", currency_field="currency_id",
                                           help="Bunga yang dibayarkan kepada anggota atas simpanan")
    biaya_lainnya = fields.Monetary(string="Biaya Lainnya", currency_field="currency_id",
                                    help="Biaya-biaya lain yang dikeluarkan koperasi")
    total_biaya = fields.Monetary(string="Total Biaya", compute="_compute_totals",
                                  store=True, currency_field="currency_id")

    # Tax calculation
    laba_sebelum_pajak = fields.Monetary(string="Laba Sebelum Pajak", compute="_compute_totals",
                                         store=True, currency_field="currency_id")

    # Fasilitas pajak untuk koperasi (pengurangan tarif)
    peredaran_bruto = fields.Monetary(string="Peredaran Bruto", currency_field="currency_id",
                                      help="Total peredaran bruto dalam satu tahun")
    dapat_fasilitas = fields.Boolean(string="Dapat Fasilitas Pajak", compute="_compute_dapat_fasilitas",
                                     store=True, help="Fasilitas pajak untuk koperasi dengan peredaran bruto < Rp50 miliar")

    pkp_fasilitas = fields.Monetary(string="PKP dengan Fasilitas", compute="_compute_pkp_fasilitas",
                                    store=True, currency_field="currency_id",
                                    help="PKP yang mendapat fasilitas pengurangan tarif")
    pkp_non_fasilitas = fields.Monetary(string="PKP Tanpa Fasilitas", compute="_compute_pkp_fasilitas",
                                        store=True, currency_field="currency_id",
                                        help="PKP yang tidak mendapat fasilitas pengurangan tarif")

    tarif_umum = fields.Float(string="Tarif Umum (%)",
                              default=22.0, help="Tarif PPh Badan umum (22%)")
    tarif_fasilitas = fields.Float(string="Tarif Fasilitas (%)", compute="_compute_tarif_fasilitas",
                                   store=True, help="Tarif PPh Badan setelah pengurangan 50% dari tarif umum")

    pajak_terutang_fasilitas = fields.Monetary(string="Pajak Fasilitas", compute="_compute_pajak_terutang",
                                               store=True, currency_field="currency_id")
    pajak_terutang_non_fasilitas = fields.Monetary(string="Pajak Non-Fasilitas", compute="_compute_pajak_terutang",
                                                   store=True, currency_field="currency_id")
    total_pajak_terutang = fields.Monetary(string="Total Pajak Terutang", compute="_compute_pajak_terutang",
                                           store=True, currency_field="currency_id")

    state = fields.Selection([
        ("draft", "Draft"),
        ("hitung", "Terhitung"),
        ("lapor", "Dilaporkan")
    ], string="Status", default="draft", tracking=True)

    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "koperasi.pajak.koperasi") or _("New")
        return super().create(vals_list)

    @api.depends("pendapatan_bunga", "pendapatan_lainnya", "biaya_operasional",
                 "biaya_bunga_simpanan", "biaya_lainnya")
    def _compute_totals(self):
        for record in self:
            record.total_pendapatan = record.pendapatan_bunga + record.pendapatan_lainnya
            record.total_biaya = (record.biaya_operasional +
                                  record.biaya_bunga_simpanan + record.biaya_lainnya)
            record.laba_sebelum_pajak = record.total_pendapatan - record.total_biaya

    @api.depends("peredaran_bruto")
    def _compute_dapat_fasilitas(self):
        for record in self:
            record.dapat_fasilitas = record.peredaran_bruto <= 50000000000  # Rp50 miliar

    @api.depends("tarif_umum")
    def _compute_tarif_fasilitas(self):
        for record in self:
            record.tarif_fasilitas = record.tarif_umum * 0.5  # 50% dari tarif umum

    @api.depends("laba_sebelum_pajak", "dapat_fasilitas", "peredaran_bruto")
    def _compute_pkp_fasilitas(self):
        batas_fasilitas = 4800000000  # Rp4,8 miliar

        for record in self:
            if record.dapat_fasilitas and record.laba_sebelum_pajak > 0:
                if record.peredaran_bruto <= batas_fasilitas:
                    # Seluruh PKP mendapat fasilitas
                    record.pkp_fasilitas = record.laba_sebelum_pajak
                    record.pkp_non_fasilitas = 0
                else:
                    # Hanya sebagian PKP yang mendapat fasilitas (proporsional)
                    proporsi_fasilitas = batas_fasilitas / record.peredaran_bruto
                    record.pkp_fasilitas = record.laba_sebelum_pajak * proporsi_fasilitas
                    record.pkp_non_fasilitas = record.laba_sebelum_pajak - record.pkp_fasilitas
            else:
                record.pkp_fasilitas = 0
                record.pkp_non_fasilitas = record.laba_sebelum_pajak if record.laba_sebelum_pajak > 0 else 0

    @api.depends("pkp_fasilitas", "pkp_non_fasilitas", "tarif_fasilitas", "tarif_umum")
    def _compute_pajak_terutang(self):
        for record in self:
            record.pajak_terutang_fasilitas = record.pkp_fasilitas * \
                (record.tarif_fasilitas / 100)
            record.pajak_terutang_non_fasilitas = record.pkp_non_fasilitas * \
                (record.tarif_umum / 100)
            record.total_pajak_terutang = (record.pajak_terutang_fasilitas +
                                           record.pajak_terutang_non_fasilitas)

    def action_hitung_pajak(self):
        self.ensure_one()
        if self.laba_sebelum_pajak <= 0:
            raise ValidationError(
                _("Laba sebelum pajak harus lebih dari 0 untuk menghitung pajak."))

        # Calculate tax components
        self._compute_dapat_fasilitas()
        self._compute_pkp_fasilitas()
        self._compute_pajak_terutang()

        self.state = "hitung"
        return True

    def action_lapor_pajak(self):
        self.ensure_one()
        if self.state != "hitung":
            raise ValidationError(
                _("Pajak harus dihitung terlebih dahulu sebelum dilaporkan."))

        self.write({
            "state": "lapor",
            "tanggal_lapor": fields.Date.today()
        })
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = "draft"
        return True

    def action_calculate_from_data(self):
        """Calculate income and expenses from transaction data for the selected year"""
        self.ensure_one()

        if self.state != "draft":
            raise ValidationError(
                _("Hanya data pajak dengan status draft yang dapat diisi otomatis."))

        year_start = date(self.tahun_pajak, 1, 1)
        year_end = date(self.tahun_pajak, 12, 31)

        # Calculate interest income from loan payments
        domain = [
            ("tanggal_pembayaran", ">=", year_start),
            ("tanggal_pembayaran", "<=", year_end),
            ("status_pembayaran", "in", ["sudah_bayar", "telat_bayar"])
        ]
        angsuran_data = self.env["koperasi.angsuran.pinjaman"].search(domain)
        pendapatan_bunga = sum(angsuran_data.mapped("jumlah_bunga_angsuran"))

        # Calculate interest expense for member savings
        domain = [
            ("tanggal_transaksi", ">=", year_start),
            ("tanggal_transaksi", "<=", year_end),
            ("tipe_transaksi", "=", "bunga_simpanan"),
            ("state", "=", "confirmed")
        ]
        bunga_simpanan_data = self.env["koperasi.transaksi.simpanan"].search(
            domain)
        biaya_bunga = sum(bunga_simpanan_data.mapped("jumlah"))

        # Calculate gross income (simplification - in a real scenario would be more comprehensive)
        # Simplification - gross income estimation
        peredaran_bruto = pendapatan_bunga * 3

        self.write({
            "pendapatan_bunga": pendapatan_bunga,
            "biaya_bunga_simpanan": biaya_bunga,
            "peredaran_bruto": peredaran_bruto
        })

        return True

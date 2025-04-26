# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import SQL
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date


class KoperasiLaporanKinerjaKeuangan(models.Model):
    _name = 'koperasi.laporan.kinerja.keuangan'
    _description = 'Laporan Kinerja Keuangan Koperasi'
    _order = 'tanggal_laporan desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Nama Laporan', required=True, tracking=True,
                       help='Masukkan nama untuk laporan kinerja keuangan')
    tanggal_laporan = fields.Date(
        string='Tanggal Laporan', default=fields.Date.today, tracking=True,
        help='Tanggal laporan ini dibuat')
    tanggal_mulai = fields.Date(
        string='Periode Awal', required=True, tracking=True,
        help='Tanggal awal periode yang akan dianalisis dalam laporan')
    tanggal_akhir = fields.Date(
        string='Periode Akhir', required=True, tracking=True,
        help='Tanggal akhir periode yang akan dianalisis dalam laporan')

    # Comparison period if needed
    include_comparison = fields.Boolean(
        string='Tampilkan Perbandingan', default=False, tracking=True,
        help='Centang untuk menampilkan perbandingan dengan periode sebelumnya')
    tanggal_mulai_komparasi = fields.Date(
        string='Periode Awal Komparasi',
        help='Tanggal awal periode pembanding untuk analisis komparatif')
    tanggal_akhir_komparasi = fields.Date(
        string='Periode Akhir Komparasi',
        help='Tanggal akhir periode pembanding untuk analisis komparatif')

    # Metrics for current period
    # Simpanan metrics
    total_simpanan_pokok = fields.Monetary(
        string='Total Simpanan Pokok', currency_field='currency_id',
        compute='_compute_simpanan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan simpanan pokok anggota koperasi per tanggal akhir laporan')
    total_simpanan_wajib = fields.Monetary(
        string='Total Simpanan Wajib', currency_field='currency_id',
        compute='_compute_simpanan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan simpanan wajib anggota koperasi per tanggal akhir laporan')
    total_simpanan_sukarela = fields.Monetary(
        string='Total Simpanan Sukarela', currency_field='currency_id',
        compute='_compute_simpanan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan simpanan sukarela anggota koperasi per tanggal akhir laporan')
    total_simpanan = fields.Monetary(
        string='Total Simpanan', currency_field='currency_id',
        compute='_compute_simpanan_metrics', store=True, readonly=False, precompute=True,
        help='Akumulasi dari seluruh jenis simpanan (pokok + wajib + sukarela) per tanggal akhir laporan')

    # Transaction metrics
    total_setoran = fields.Monetary(
        string='Total Setoran Periode Ini', currency_field='currency_id',
        compute='_compute_transaction_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan setoran dari anggota selama periode laporan')
    total_penarikan = fields.Monetary(
        string='Total Penarikan Periode Ini', currency_field='currency_id',
        compute='_compute_transaction_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan penarikan oleh anggota selama periode laporan')
    net_cash_flow_simpanan = fields.Monetary(
        string='Arus Kas Bersih Simpanan', currency_field='currency_id',
        compute='_compute_transaction_metrics', store=True, readonly=False, precompute=True,
        help='Selisih antara total setoran dan penarikan selama periode laporan')

    # Loan metrics
    total_pinjaman_aktif = fields.Monetary(
        string='Total Pinjaman Aktif', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan sisa pinjaman yang masih aktif per tanggal akhir laporan')
    total_pinjaman_baru = fields.Monetary(
        string='Total Pinjaman Baru Periode Ini', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan pinjaman baru yang disetujui selama periode laporan')
    total_pelunasan = fields.Monetary(
        string='Total Pelunasan Periode Ini', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan pinjaman yang dilunasi selama periode laporan')
    total_angsuran_diterima = fields.Monetary(
        string='Total Angsuran Diterima', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan pembayaran angsuran yang diterima selama periode laporan')
    total_pokok_diterima = fields.Monetary(
        string='Total Pokok Diterima', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan pokok pinjaman yang dibayarkan selama periode laporan')
    total_bunga_diterima = fields.Monetary(
        string='Total Bunga Diterima', currency_field='currency_id',
        compute='_compute_loan_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah keseluruhan bunga pinjaman yang dibayarkan selama periode laporan')

    # Performance metrics
    jumlah_anggota_aktif = fields.Integer(
        string='Jumlah Anggota Aktif',
        compute='_compute_performance_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah anggota koperasi dengan status aktif per tanggal akhir laporan')
    jumlah_pinjaman_aktif = fields.Integer(
        string='Jumlah Pinjaman Aktif',
        compute='_compute_performance_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah pinjaman dengan status aktif per tanggal akhir laporan')
    jumlah_pinjaman_bermasalah = fields.Integer(
        string='Jumlah Pinjaman Bermasalah',
        compute='_compute_performance_metrics', store=True, readonly=False, precompute=True,
        help='Jumlah pinjaman dengan status menunggak per tanggal akhir laporan')
    rasio_pinjaman_bermasalah = fields.Float(
        string='Rasio Pinjaman Bermasalah (%)', digits=(5, 2),
        compute='_compute_performance_metrics', store=True, readonly=False, precompute=True,
        help='Persentase pinjaman bermasalah terhadap total pinjaman aktif')

    # Comparison metrics (if comparison is enabled)
    simpanan_growth = fields.Float(
        string='Pertumbuhan Simpanan (%)', digits=(5, 2),
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Persentase pertumbuhan total simpanan dibandingkan dengan periode komparasi')
    pinjaman_growth = fields.Float(
        string='Pertumbuhan Pinjaman (%)', digits=(5, 2),
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Persentase pertumbuhan total pinjaman aktif dibandingkan dengan periode komparasi')
    bunga_growth = fields.Float(
        string='Pertumbuhan Pendapatan Bunga (%)', digits=(5, 2),
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Persentase pertumbuhan total bunga yang diterima dibandingkan dengan periode komparasi')

    # Comparison period values
    comp_total_simpanan = fields.Monetary(
        string='Total Simpanan (Komparasi)', currency_field='currency_id',
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Total simpanan pada periode komparasi')
    comp_total_pinjaman_aktif = fields.Monetary(
        string='Total Pinjaman Aktif (Komparasi)', currency_field='currency_id',
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Total pinjaman aktif pada periode komparasi')
    comp_total_bunga_diterima = fields.Monetary(
        string='Total Bunga Diterima (Komparasi)', currency_field='currency_id',
        compute='_compute_comparison_metrics', store=True, readonly=False,
        help='Total bunga yang diterima pada periode komparasi')

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id,
        help='Mata uang yang digunakan dalam laporan')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated')
    ], string='Status', default='draft', tracking=True,
        help='Status laporan: Draft (belum diproses) atau Generated (sudah diproses)')

    def action_generate_report(self):
        """Generate the financial performance report for the specified period.

        This method computes all metrics for the current period and comparison period if enabled.
        """
        self.ensure_one()

        if self.state == 'generated':
            return True

        # Invalidate previous calculations to ensure fresh computation
        self.invalidate_recordset(['total_simpanan_pokok', 'total_simpanan_wajib',
                                  'total_simpanan_sukarela', 'total_simpanan'])

        # Calculate metrics for current period
        self._compute_simpanan_metrics()
        self._compute_transaction_metrics()
        self._compute_loan_metrics()
        self._compute_performance_metrics()

        # Calculate comparison if enabled
        if self.include_comparison and self.tanggal_mulai_komparasi and self.tanggal_akhir_komparasi:
            self._compute_comparison_metrics()

        self.state = 'generated'
        return True

    def action_view_simpanan(self):
        """Open a view showing the simpanan records included in this report."""
        self.ensure_one()
        return {
            'name': _('Simpanan'),
            'view_mode': 'list,form',
            'res_model': 'koperasi.simpanan',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                'create': False
            }
        }

    def action_view_pinjaman(self):
        """Open a view showing the active loans included in this report."""
        self.ensure_one()
        domain = [
            ('status_pinjaman', 'in', ['aktif', 'menunggak'])
        ]
        return {
            'name': _('Pinjaman Aktif'),
            'view_mode': 'list,form',
            'res_model': 'koperasi.pinjaman',
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': {
                'create': False
            }
        }

    def action_view_pajak_simpanan(self):
        """Open a view showing the tax records for savings in this period."""
        self.ensure_one()
        domain = [
            ('tanggal_pemotongan', '>=', self.tanggal_mulai),
            ('tanggal_pemotongan', '<=', self.tanggal_akhir)
        ]
        return {
            'name': _('Pajak Simpanan'),
            'view_mode': 'list,form',
            'res_model': 'koperasi.pajak.simpanan',
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': {
                'create': False
            }
        }

    @api.depends('tanggal_akhir')
    def _compute_simpanan_metrics(self):
        """Calculate savings metrics as of the end date.

        Computes:
        - Total basic savings (simpanan pokok)
        - Total mandatory savings (simpanan wajib)
        - Total voluntary savings (simpanan sukarela)
        - Total savings (all types combined)
        """
        for record in self:
            if not record.tanggal_akhir:
                continue

            # Query to get all savings records and their balances
            simpanan_records = self.env['koperasi.simpanan'].search([])

            # Query for transactions to get the state at the end date
            domain = [
                ('tanggal_transaksi', '<=', record.tanggal_akhir),
                ('state', '=', 'confirmed')
            ]

            all_transactions = self.env['koperasi.transaksi.simpanan'].search(
                domain)

            # Calculate total savings by type
            simpanan_pokok = sum(simpanan_records.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'pokok').mapped('saldo'))
            simpanan_wajib = sum(simpanan_records.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'wajib').mapped('saldo'))
            simpanan_sukarela = sum(simpanan_records.filtered(
                lambda s: s.jenis_simpanan_id.kode == 'sukarela').mapped('saldo'))

            record.total_simpanan_pokok = simpanan_pokok
            record.total_simpanan_wajib = simpanan_wajib
            record.total_simpanan_sukarela = simpanan_sukarela
            record.total_simpanan = simpanan_pokok + simpanan_wajib + simpanan_sukarela

    @api.depends('tanggal_mulai', 'tanggal_akhir')
    def _compute_transaction_metrics(self):
        """Calculate transaction metrics for the period.

        Computes:
        - Total deposits during the period
        - Total withdrawals during the period
        - Net cash flow (deposits - withdrawals)
        """
        for record in self:
            if not record.tanggal_mulai or not record.tanggal_akhir:
                continue

            # Query for transactions within the period
            domain = [
                ('tanggal_transaksi', '>=', record.tanggal_mulai),
                ('tanggal_transaksi', '<=', record.tanggal_akhir),
                ('state', '=', 'confirmed')
            ]

            transactions = self.env['koperasi.transaksi.simpanan'].search(
                domain)

            # Calculate deposits and withdrawals
            deposit_types = ['setor', 'pendaftaran_pokok', 'potongan_wajib']
            withdrawal_types = ['tarik', 'pengembalian_keluar']

            deposits = sum(transactions.filtered(
                lambda t: t.tipe_transaksi in deposit_types).mapped('jumlah'))
            withdrawals = sum(transactions.filtered(
                lambda t: t.tipe_transaksi in withdrawal_types).mapped('jumlah'))

            record.total_setoran = deposits
            record.total_penarikan = withdrawals
            record.net_cash_flow_simpanan = deposits - withdrawals

    @api.depends('tanggal_mulai', 'tanggal_akhir')
    def _compute_loan_metrics(self):
        """Calculate loan metrics for the period.

        Computes:
        - Total active loans
        - Total new loans in the period
        - Total loan repayments in the period
        - Total installments received
        - Total principal received
        - Total interest received
        """
        for record in self:
            if not record.tanggal_mulai or not record.tanggal_akhir:
                continue

            # Get active loans
            active_loan_domain = [
                ('status_pinjaman', 'in', ['aktif', 'menunggak'])
            ]
            pinjaman_aktif = self.env['koperasi.pinjaman'].search(
                active_loan_domain)

            # Get new loans in the period
            new_loan_domain = [
                ('tanggal_persetujuan', '>=', record.tanggal_mulai),
                ('tanggal_persetujuan', '<=', record.tanggal_akhir),
                ('status_pinjaman', '!=', 'pengajuan')
            ]
            pinjaman_baru = self.env['koperasi.pinjaman'].search(
                new_loan_domain)

            # Get loan payments in the period
            payment_domain = [
                ('tanggal_pembayaran', '>=', record.tanggal_mulai),
                ('tanggal_pembayaran', '<=', record.tanggal_akhir),
                ('status_pembayaran', 'in', ['sudah_bayar', 'telat_bayar'])
            ]
            angsuran_dibayar = self.env['koperasi.angsuran.pinjaman'].search(
                payment_domain)

            # Get fully paid loans in this period
            lunas_domain = [
                ('status_pinjaman', '=', 'lunas'),
                ('tanggal_jatuh_tempo_lunas', '>=', record.tanggal_mulai),
                ('tanggal_jatuh_tempo_lunas', '<=', record.tanggal_akhir)
            ]
            pinjaman_lunas = self.env['koperasi.pinjaman'].search(lunas_domain)

            # Calculate metrics
            record.total_pinjaman_aktif = sum(
                pinjaman_aktif.mapped('sisa_pinjaman'))
            record.total_pinjaman_baru = sum(
                pinjaman_baru.mapped('jumlah_pokok'))
            record.total_angsuran_diterima = sum(
                angsuran_dibayar.mapped('jumlah_dibayar'))
            record.total_pokok_diterima = sum(
                angsuran_dibayar.mapped('jumlah_pokok_angsuran'))
            record.total_bunga_diterima = sum(
                angsuran_dibayar.mapped('jumlah_bunga_angsuran'))
            record.total_pelunasan = sum(
                pinjaman_lunas.mapped('total_pinjaman'))

    @api.depends('tanggal_akhir')
    def _compute_performance_metrics(self):
        """Calculate performance metrics.

        Computes:
        - Number of active members
        - Number of active loans
        - Number of problematic loans
        - NPL ratio (non-performing loans)
        """
        for record in self:
            if not record.tanggal_akhir:
                continue

            # Count active members
            anggota_domain = [('status_keanggotaan', '=', 'aktif')]
            record.jumlah_anggota_aktif = self.env['koperasi.anggota'].search_count(
                anggota_domain)

            # Count active loans
            pinjaman_aktif_domain = [('status_pinjaman', '=', 'aktif')]
            pinjaman_aktif_count = self.env['koperasi.pinjaman'].search_count(
                pinjaman_aktif_domain)
            record.jumlah_pinjaman_aktif = pinjaman_aktif_count

            # Count problematic loans
            pinjaman_bermasalah_domain = [
                ('status_pinjaman', '=', 'menunggak')]
            pinjaman_bermasalah_count = self.env['koperasi.pinjaman'].search_count(
                pinjaman_bermasalah_domain)
            record.jumlah_pinjaman_bermasalah = pinjaman_bermasalah_count

            # Calculate NPL ratio
            total_loans_count = pinjaman_aktif_count + pinjaman_bermasalah_count
            record.rasio_pinjaman_bermasalah = (
                pinjaman_bermasalah_count / total_loans_count * 100) if total_loans_count else 0

    @api.depends('include_comparison', 'tanggal_mulai_komparasi', 'tanggal_akhir_komparasi',
                 'total_simpanan', 'total_pinjaman_aktif', 'total_bunga_diterima')
    def _compute_comparison_metrics(self):
        """Calculate comparison metrics for historical analysis.

        Computes:
        - Total savings, loans, and interest received in comparison period
        - Growth percentages between current and comparison periods
        """
        for record in self:
            if not (record.include_comparison and record.tanggal_mulai_komparasi and record.tanggal_akhir_komparasi):
                record.comp_total_simpanan = 0
                record.comp_total_pinjaman_aktif = 0
                record.comp_total_bunga_diterima = 0
                record.simpanan_growth = 0
                record.pinjaman_growth = 0
                record.bunga_growth = 0
                continue

            # Save current period dates
            current_start = record.tanggal_mulai
            current_end = record.tanggal_akhir

            # Temporarily set to comparison period
            record.tanggal_mulai = record.tanggal_mulai_komparasi
            record.tanggal_akhir = record.tanggal_akhir_komparasi

            # For comparison period, calculate total savings
            simpanan_records = self.env['koperasi.simpanan'].search([])
            comp_simpanan_total = sum(simpanan_records.mapped('saldo'))
            record.comp_total_simpanan = comp_simpanan_total

            # Calculate total active loans in comparison period
            comp_loan_domain = [
                ('status_pinjaman', 'in', ['aktif', 'menunggak']),
                ('tanggal_persetujuan', '<=', record.tanggal_akhir_komparasi)
            ]
            comp_pinjaman_aktif = self.env['koperasi.pinjaman'].search(
                comp_loan_domain)
            record.comp_total_pinjaman_aktif = sum(
                comp_pinjaman_aktif.mapped('sisa_pinjaman'))

            # Calculate total interest received in comparison period
            comp_payment_domain = [
                ('tanggal_pembayaran', '>=', record.tanggal_mulai_komparasi),
                ('tanggal_pembayaran', '<=', record.tanggal_akhir_komparasi),
                ('status_pembayaran', 'in', ['sudah_bayar', 'telat_bayar'])
            ]
            comp_angsuran_dibayar = self.env['koperasi.angsuran.pinjaman'].search(
                comp_payment_domain)
            record.comp_total_bunga_diterima = sum(
                comp_angsuran_dibayar.mapped('jumlah_bunga_angsuran'))

            # Calculate growth percentages
            record.simpanan_growth = self._calculate_growth_percentage(
                record.total_simpanan, record.comp_total_simpanan)
            record.pinjaman_growth = self._calculate_growth_percentage(
                record.total_pinjaman_aktif, record.comp_total_pinjaman_aktif)
            record.bunga_growth = self._calculate_growth_percentage(
                record.total_bunga_diterima, record.comp_total_bunga_diterima)

            # Restore current period dates
            record.tanggal_mulai = current_start
            record.tanggal_akhir = current_end

    def _calculate_growth_percentage(self, current_value, previous_value):
        """Helper method to calculate growth percentage between two values.

        Args:
            current_value: The current period value
            previous_value: The comparison period value

        Returns:
            float: Growth percentage or 100 if previous value was 0
        """
        if previous_value and previous_value > 0:
            return ((current_value - previous_value) / previous_value) * 100
        elif current_value > 0 and not previous_value:
            return 100  # If previous was 0 and current is positive, growth is 100%
        else:
            return 0

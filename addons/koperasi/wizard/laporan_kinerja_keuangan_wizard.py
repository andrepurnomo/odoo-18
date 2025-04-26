# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo.tools import SQL


class KoperasiLaporanKinerjaKeuanganWizard(models.TransientModel):
    _name = 'koperasi.wizard.laporan.kinerja.keuangan'
    _description = 'Wizard Laporan Kinerja Keuangan'

    name = fields.Char(string='Nama Laporan', required=True,
                       default=lambda self: _('Laporan Kinerja Keuangan - %s') % fields.Date.today())

    # Period selection
    period_type = fields.Selection([
        ('month', 'Bulan'),
        ('quarter', 'Triwulan'),
        ('semester', 'Semester'),
        ('year', 'Tahun'),
        ('custom', 'Kustom')
    ], string='Tipe Periode', default='month', required=True)

    # For custom period
    tanggal_mulai = fields.Date(string='Periode Awal', required=True,
                                compute='_compute_tanggal_period', store=True, readonly=False, precompute=True)
    tanggal_akhir = fields.Date(string='Periode Akhir', required=True,
                                compute='_compute_tanggal_period', store=True, readonly=False, precompute=True)

    # Comparison
    include_comparison = fields.Boolean(
        string='Tampilkan Perbandingan', default=False)
    comparison_period_type = fields.Selection([
        ('previous_period', 'Periode Sebelumnya'),
        ('same_period_last_year', 'Periode Sama Tahun Lalu'),
        ('custom', 'Kustom')
    ], string='Tipe Perbandingan', default='previous_period')

    # For custom comparison period
    tanggal_mulai_komparasi = fields.Date(string='Periode Awal Komparasi',
                                          compute='_compute_tanggal_komparasi', store=True, readonly=False)
    tanggal_akhir_komparasi = fields.Date(string='Periode Akhir Komparasi',
                                          compute='_compute_tanggal_komparasi', store=True, readonly=False)

    @api.depends('period_type')
    def _compute_tanggal_period(self):
        today = date.today()

        for record in self:
            if record.period_type == 'month':
                record.tanggal_mulai = today.replace(day=1)
                next_month = today.replace(day=28) + relativedelta(days=4)
                record.tanggal_akhir = (
                    next_month - relativedelta(days=next_month.day)).replace(day=1) - relativedelta(days=1)

            elif record.period_type == 'quarter':
                quarter = ((today.month - 1) // 3) + 1
                record.tanggal_mulai = date(
                    today.year, (quarter - 1) * 3 + 1, 1)
                if quarter < 4:
                    record.tanggal_akhir = date(
                        today.year, quarter * 3 + 1, 1) - relativedelta(days=1)
                else:
                    record.tanggal_akhir = date(today.year, 12, 31)

            elif record.period_type == 'semester':
                semester = 1 if today.month <= 6 else 2
                if semester == 1:
                    record.tanggal_mulai = date(today.year, 1, 1)
                    record.tanggal_akhir = date(today.year, 6, 30)
                else:
                    record.tanggal_mulai = date(today.year, 7, 1)
                    record.tanggal_akhir = date(today.year, 12, 31)

            elif record.period_type == 'year':
                record.tanggal_mulai = date(today.year, 1, 1)
                record.tanggal_akhir = date(today.year, 12, 31)

            # For custom period, we don't modify the dates that were manually set by the user

    @api.depends('include_comparison', 'comparison_period_type', 'tanggal_mulai', 'tanggal_akhir')
    def _compute_tanggal_komparasi(self):
        for record in self:
            if record.include_comparison and record.tanggal_mulai and record.tanggal_akhir:
                if record.comparison_period_type == 'previous_period':
                    # Calculate previous period of same length
                    delta = record.tanggal_akhir - record.tanggal_mulai
                    record.tanggal_akhir_komparasi = record.tanggal_mulai - \
                        relativedelta(days=1)
                    record.tanggal_mulai_komparasi = record.tanggal_akhir_komparasi - delta

                elif record.comparison_period_type == 'same_period_last_year':
                    # Same period last year
                    record.tanggal_mulai_komparasi = record.tanggal_mulai - \
                        relativedelta(years=1)
                    record.tanggal_akhir_komparasi = record.tanggal_akhir - \
                        relativedelta(years=1)

                # For custom comparison period, we don't modify the dates that were manually set by the user

    def action_generate_report(self):
        self.ensure_one()

        # Create the report
        report_vals = {
            'name': self.name,
            'tanggal_laporan': fields.Date.today(),
            'tanggal_mulai': self.tanggal_mulai,
            'tanggal_akhir': self.tanggal_akhir,
            'include_comparison': self.include_comparison,
        }

        if self.include_comparison:
            report_vals.update({
                'tanggal_mulai_komparasi': self.tanggal_mulai_komparasi,
                'tanggal_akhir_komparasi': self.tanggal_akhir_komparasi,
            })

        laporan = self.env['koperasi.laporan.kinerja.keuangan'].create(
            report_vals)

        # Generate the report data
        laporan.action_generate_report()

        # Open the report
        return {
            'name': _('Laporan Kinerja Keuangan'),
            'view_mode': 'form',
            'res_model': 'koperasi.laporan.kinerja.keuangan',
            'res_id': laporan.id,
            'type': 'ir.actions.act_window',
        }

    def _generate_report_data_sql(self, date_from, date_to):
        """Get report data using SQL query for better performance"""
        self.env.cr.execute(SQL("""
            SELECT 
                account.id AS account_id,
                account.code AS account_code,
                account.name AS account_name,
                SUM(aml.balance) AS balance
            FROM account_move_line aml
            JOIN account_account account ON aml.account_id = account.id
            JOIN account_move move ON aml.move_id = move.id
            WHERE move.state = 'posted'
                AND move.company_id = %(company_id)s
                AND move.date BETWEEN %(date_from)s AND %(date_to)s
            GROUP BY account.id, account.code, account.name
            ORDER BY account.code
        """, company_id=self.env.company.id, date_from=date_from, date_to=date_to))

        return self.env.cr.dictfetchall()

    def fetch_comparison_data(self):
        """Fetch comparison data for the report"""
        if not self.include_comparison:
            return {}

        comparison_data = self._generate_report_data_sql(
            self.tanggal_mulai_komparasi,
            self.tanggal_akhir_komparasi
        )

        # Convert to dictionary for easier access
        return {item['account_id']: item for item in comparison_data}

    @api.model
    def get_default_period(self):
        """Helper method to get default period based on current date"""
        today = date.today()
        return {
            'period_type': 'month',
            'tanggal_mulai': today.replace(day=1),
            'tanggal_akhir': (today.replace(day=28) + relativedelta(days=4) -
                              relativedelta(days=(today.replace(day=28) + relativedelta(days=4)).day)).replace(day=1) -
            relativedelta(days=1)
        }

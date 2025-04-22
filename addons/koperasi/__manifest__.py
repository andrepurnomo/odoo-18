# -*- coding: utf-8 -*-
{
    'name': 'Koperasi',
    'version': '1.0',
    'category': 'Koperasi',
    'summary': 'Sistem Informasi Koperasi',
    'description': """
        Modul untuk Pengelolaan Koperasi
        ===============================
        
        Fitur:
        - Pengelolaan Anggota
        - Pengelolaan Simpanan (Pokok, Wajib, Sukarela)
        - Pengelolaan Pinjaman dan Angsuran
        - Perhitungan SHU
        - Laporan-laporan
    """,
    'author': 'Semakode',
    'website': 'https://semakodeapp.web.app/',
    'depends': ['base', 'mail'],
    'data': [
        'security/koperasi_security.xml',
        'security/ir.model.access.csv',
        'data/koperasi_data.xml',
        'views/anggota_views.xml',
        'views/simpanan_views.xml',
        'views/transaksi_simpanan_views.xml',
        'views/pinjaman_views.xml',
        'views/angsuran_pinjaman_views.xml',
        'views/dashboard_views.xml',
        'views/shu_views.xml',
        'views/laporan_shu_views.xml',
        'views/laporan_views.xml',
        'views/koperasi_menu_views.xml',
        'wizard/bayar_angsuran_views.xml',
        'wizard/tolak_pinjaman_views.xml',
        'wizard/mulai_angsuran_views.xml',
        'wizard/lunasi_pinjaman_views.xml',
        'wizard/keluar_anggota_views.xml',
    ],
    'demo': [
        'data/koperasi_demo_data.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

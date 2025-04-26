# Alur Kerja Sistem Koperasi

## 1. Pendaftaran dan Pengelolaan Anggota

### Pendaftaran Anggota Baru
- Anggota baru didaftarkan dengan data pribadi (nama, NIK, alamat, telepon, email)
- Sistem otomatis membuat nomor anggota unik menggunakan sequence
- Anggota baru otomatis berstatus "aktif" dengan tanggal bergabung saat ini
- Saat pendaftaran, anggota perlu melakukan setoran awal simpanan pokok

### Pengelolaan Status Anggota
- Anggota dapat berstatus "aktif" atau "non_aktif"
- Untuk mengubah status menjadi non-aktif, gunakan wizard "Keluarkan Anggota"
- Sistem akan memeriksa apakah anggota masih memiliki pinjaman aktif
- Jika tidak ada pinjaman aktif, sistem akan:
  - Mengembalikan seluruh simpanan (pokok, wajib, sukarela)
  - Membuat transaksi pengembalian untuk setiap jenis simpanan
  - Mengubah status menjadi non-aktif dan mencatat tanggal keluar

## 2. Pengelolaan Simpanan

### Jenis Simpanan
Terdapat 3 jenis simpanan utama:
- Simpanan Pokok (kode: "pokok") - dibayar sekali saat pendaftaran
- Simpanan Wajib (kode: "wajib") - dibayar secara berkala
- Simpanan Sukarela (kode: "sukarela") - bisa disetor/ditarik kapan saja

### Transaksi Simpanan
#### Tipe transaksi simpanan:
- Setor - menambah saldo simpanan
- Tarik - mengurangi saldo simpanan
- Potongan Wajib - pembayaran simpanan wajib
- Pendaftaran Pokok - pembayaran simpanan pokok saat mendaftar
- Pengembalian Keluar - pengembalian simpanan saat anggota keluar

#### Alur transaksi:
1. Buat transaksi dengan status "draft"
2. Konfirmasi transaksi ("action_confirm")
3. Sistem akan mencatat saldo sebelum transaksi
4. Sistem akan memperbarui saldo simpanan anggota sesuai tipe transaksi
5. Sistem akan mencatat saldo setelah transaksi
6. Status transaksi menjadi "confirmed"

#### Pembatalan transaksi:
1. Pilih transaksi yang akan dibatalkan
2. Jalankan "action_cancel"
3. Sistem akan mengembalikan saldo ke posisi semula
4. Status transaksi menjadi "cancelled"

## 3. Pengelolaan Pinjaman

### Pengajuan Pinjaman
- Anggota mengajukan pinjaman dengan status awal "pengajuan"
- Data pinjaman mencakup:
  - Jumlah pokok pinjaman
  - Tenor (bulan)
  - Bunga per bulan (%)
  - Tanggal pengajuan
- Sistem otomatis menghitung total bunga, total pinjaman, dan angsuran bulanan

### Persetujuan Pinjaman
- Admin/petugas memproses pengajuan pinjaman
- Opsi persetujuan:
  - Setujui (action_approve) - status menjadi "disetujui"
  - Tolak (action_reject) - status menjadi "ditolak" dengan alasan penolakan
- Jika disetujui, tentukan tanggal mulai angsuran melalui wizard
- Setelah tanggal mulai ditentukan, aktifkan pinjaman (action_activate)

### Aktivasi Pinjaman
- Sistem mengubah status pinjaman menjadi "aktif"
- Sistem membuat jadwal angsuran otomatis (satu record per bulan)
- Untuk setiap angsuran, sistem menentukan:
  - Angsuran ke-berapa
  - Jumlah pokok angsuran
  - Jumlah bunga angsuran
  - Tanggal jatuh tempo

## 4. Pengelolaan Angsuran

### Pembayaran Angsuran
- Untuk membayar angsuran, gunakan wizard "Bayar Angsuran"
- Pilih angsuran yang akan dibayar
- Isi data pembayaran:
  - Tanggal pembayaran
  - Jumlah dibayar
  - Metode pembayaran (tunai, transfer, potong simpanan)
- Jika metode "potong simpanan", pilih simpanan sukarela yang akan dipotong
- Jika pembayaran telat, sistem otomatis menghitung denda (0,5% per hari keterlambatan)
- Setelah konfirmasi, status angsuran berubah menjadi:
  - "sudah_bayar" jika tepat waktu
  - "telat_bayar" jika melewati jatuh tempo
- Jika metode pembayaran "potong simpanan", sistem akan membuat transaksi penarikan simpanan

### Pemeriksaan Status Pinjaman
Sistem secara otomatis memeriksa status pinjaman (action_check_status):
- Jika ada angsuran yang telat, status pinjaman menjadi "menunggak"
- Jika semua angsuran terbayar, status pinjaman menjadi "lunas"
- Jika tidak ada angsuran telat dan belum lunas, status tetap "aktif"

### Pelunasan Dipercepat
- Untuk melunasi pinjaman sebelum waktunya, gunakan wizard "Lunasi Pinjaman"
- Pilih metode pembayaran (tunai, transfer, potong simpanan)
- Sistem akan:
  - Menandai semua angsuran yang belum dibayar sebagai "sudah_bayar"
  - Mencatat tanggal pelunasan
  - Mengubah status pinjaman menjadi "lunas"
  - Jika metode "potong simpanan", membuat transaksi penarikan simpanan

## 5. Dashboard dan Laporan

### Dashboard Koperasi
Menampilkan ringkasan data penting:
- Total anggota aktif dan anggota baru bulan ini
- Total simpanan (pokok, wajib, sukarela)
- Total pinjaman aktif, pengajuan, dan menunggak
- Total angsuran jatuh tempo hari ini dan angsuran telat
- Total pendapatan bunga tahun ini

### Laporan Kinerja Keuangan
Buat laporan kinerja keuangan dengan wizard:
- Pilih periode laporan (bulan, triwulan, semester, tahun, kustom)
- Opsional: aktifkan perbandingan dengan periode sebelumnya
- Sistem akan menghitung:
  - Total simpanan (pokok, wajib, sukarela)
  - Total transaksi (setoran, penarikan)
  - Total pinjaman aktif, baru, dan pelunasan
  - Angsuran diterima (pokok dan bunga)
  - Metrik kinerja (rasio pinjaman bermasalah)
  - Perbandingan dengan periode lain jika diaktifkan

### Laporan SHU (Sisa Hasil Usaha)
Buat laporan SHU dengan wizard:
- Pilih tahun buku
- Sistem akan menghitung:
  - Total pendapatan bunga yang sudah diterima
  - Total pendapatan bunga yang akan masuk (belum dibayar)
  - Total pendapatan bunga keseluruhan

## 6. Alur Kerja Keseluruhan

### Pendaftaran Anggota
1. Daftarkan anggota baru
2. Lakukan setoran simpanan pokok

### Setoran Simpanan Rutin
- Anggota melakukan setoran simpanan wajib secara rutin
- Anggota dapat menambah simpanan sukarela kapan saja

### Pengajuan dan Persetujuan Pinjaman
1. Anggota mengajukan pinjaman
2. Admin/petugas menyetujui atau menolak pengajuan
3. Jika disetujui, tentukan tanggal mulai angsuran dan aktifkan pinjaman

### Pembayaran Angsuran
- Anggota membayar angsuran bulanan sesuai jadwal
- Jika terlambat, sistem mengenakan denda
- Anggota dapat melunasi pinjaman lebih cepat

### Monitoring dan Pelaporan
- Admin/petugas memantau status anggota, simpanan, dan pinjaman melalui dashboard
- Membuat laporan kinerja keuangan dan SHU secara berkala

### Penutupan Keanggotaan
1. Anggota yang ingin keluar harus melunasi semua pinjaman
2. Admin/petugas memproses pengembalian simpanan
3. Status anggota diubah menjadi non-aktif

## Laporan Kinerja Keuangan

Fitur Laporan Kinerja Keuangan pada modul Koperasi memungkinkan pengurus koperasi untuk membuat dan menganalisis laporan komprehensif tentang kinerja keuangan koperasi dalam periode tertentu.

### Fitur Utama
- **Pemilihan Periode**: Laporan dapat dibuat untuk periode Bulanan, Triwulanan, Semester, Tahunan, atau periode Kustom sesuai kebutuhan.
- **Analisis Perbandingan**: Mendukung perbandingan kinerja dengan periode sebelumnya, periode yang sama tahun lalu, atau periode kustom untuk analisis pertumbuhan.
- **Metrik Simpanan**: Menampilkan total simpanan pokok, wajib, dan sukarela beserta pertumbuhannya.
- **Metrik Transaksi**: Menyajikan data setoran, penarikan, dan arus kas bersih simpanan.
- **Metrik Pinjaman**: Mencakup total pinjaman aktif, pinjaman baru, pelunasan, dan pertumbuhan pinjaman.
- **Metrik Angsuran**: Menampilkan total angsuran yang diterima, pokok yang diterima, dan bunga yang diterima.
- **Indikator Kinerja**: Menyajikan jumlah anggota aktif, jumlah pinjaman aktif, jumlah pinjaman bermasalah, dan rasio pinjaman bermasalah.

### Cara Penggunaan
1. Pilih menu Laporan Kinerja Keuangan di bagian Laporan
2. Tentukan nama laporan dan periode yang ingin dianalisis
3. Jika diperlukan, aktifkan fitur perbandingan dan pilih periode perbandingan
4. Klik tombol Generate Report untuk membuat laporan
5. Laporan akan menampilkan data lengkap dalam bentuk yang mudah dibaca dan dianalisis

### Manfaat
- Memberikan gambaran menyeluruh tentang kondisi keuangan koperasi
- Membantu identifikasi tren pertumbuhan atau penurunan kinerja
- Memudahkan pengurus dalam pengambilan keputusan strategis
- Membantu mendeteksi permasalahan seperti tingginya rasio pinjaman bermasalah
- Mendukung pelaporan rutin kepada anggota dan pemangku kepentingan lainnya

Dengan Laporan Kinerja Keuangan, pengurus koperasi dapat memonitor kesehatan keuangan koperasi secara berkala dan mengambil keputusan yang tepat untuk pertumbuhan koperasi yang berkelanjutan.
*Setiap aktivitas di atas tercatat dalam sistem dan dapat dilacak melalui fitur tracking yang terintegrasi dalam aplikasi.*

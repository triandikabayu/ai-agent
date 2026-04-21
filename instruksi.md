# Panduan Peningkatan (Improvement) Proyek AI-Agent

Dokumen ini berisi analisis area proyek yang perlu ditingkatkan, serta draft instruksi bertahap yang sangat mudah diikuti oleh _junior programmer_ atau model AI.

## 📌 Area Utama yang Perlu Di-improve:

1. **`main.py` Terlalu Panjang dan Sulit Dikelola:** 
   Fungsi `handle_slash_command` menggunakan blok rantai `if-elif` yang sangat panjang (lebih dari 150 baris). Jika di masa depan jumlah command `/` bertambah, file ini akan sangat sulit dibaca (Spaghetti Code). Ini harus dipecah ke dalam sistem berbasis modul/dictionary.
2. **Tidak Adanya Sistem Unit Testing (Pengujian):** 
   Tidak ada direktori `tests/` di root proyek. Karena agen AI sering kali melakukan kegagalan acak, *tools* yang krusial (seperti fungsi membaca/menulis file di `file_tools.py`) wajib memiliki test mandiri.
3. **Alat Edit File (`edit_file`) Kurang Aman:**
   Pada `tools/file_tools.py`, alat `edit_file` mengganti konten hanya berdasarkan teks menggunakan `content.replace(..., 1)`. Ini lumayan berisiko karena jika ada potongan kode yang kebetulan sama di baris lain, file bisa menjadi rusak. Seharusnya ada fitur *auto-backup* file terlebih dahulu sebelum melakukan edit programatik.

---

## 📝 Draft Instruksi Eksekusi

Kumpulan instruksi di bawah ini dirancang dengan gaya **"Checklist & Langkah Eksekusi Eksplisit"** yang sangat ramah dan mudah dipahami agar meminimalisir kesalahan (bug) atau halusinasi dari AI.

### Bagian 1: Instruksi untuk Refactor `main.py` (Antarmuka Command)

Tugas Anda adalah merapikan file `main.py`. Saat ini `main.py` memiliki fungsi `handle_slash_command` yang menggunakan terlalu banyak blok `if-elif`. Tolong ikuti instruksi berikut secara bertahap:

1. Buat direktori baru bernama `cli/` di root direktori proyek.
2. Di dalam direktori `cli/`, buat dua file kosong: `__init__.py` dan `commands.py`.
3. Pindahkan semua logika yang meng-handle masing-masing slash command (seperti `/search`, `/learn`, `/clear`, `/exit`) dari `main.py` ke dalam `cli/commands.py`. 
4. Di file `cli/commands.py`, buatlah fungsi-fungsi kecil terpisah untuk setiap command, contohnya: `handle_search(...)`, `handle_learn(...)`, dan seterusnya.
5. Buat sebuah variabel "dictionary" (pemetaan) bernama `COMMAND_REGISTRY` di dalam `cli/commands.py` untuk menghubungkan teks command dengan fungsi barunya, contoh:
   ```python
   COMMAND_REGISTRY = {
       "/search": handle_search,
       "/learn": handle_learn,
       # tambahkan sisa command di sini
   }
   ```
6. Kembali ke `main.py`, ubah fungsi `handle_slash_command` agar memakai `COMMAND_REGISTRY` tersebut. Buat agar fungsinya langsung memanggil perintah dari dictionary, tanpa rantai `if-elif` panjang sama sekali.
7. Simpan file `main.py` dan pastikan Anda tidak terhapus pesan "Welcome/Banner" di dalamnya.

### Bagian 2: Instruksi untuk Fitur Auto-Backup di `file_tools.py`

Tugas Anda adalah menambahkan fitur "Keamanan/Backup" saat agen sedang memodifikasi kode. Silakan buka file `tools/file_tools.py` lalu ikuti instruksi ini:

1. Di awal file `tools/file_tools.py`, pastikan ada impor library `shutil` (tulis `import shutil`).
2. Cari fungsi bernama `edit_file(...)`.
3. Di dalam fungsi `edit_file(...)`, SEBELUM mengeksekusi operasi `new_content = content.replace(...)`, Anda harus menambahkan sintaks untuk membackup file orisinal.
4. Buat variabel backup misalnya: `backup_path = Path(file_path).with_suffix(".bak")`.
5. Gunakan `shutil.copy2(path, backup_path)` untuk menduplikat file tersebut sebagai file backup.
6. Berikan validasi, jika proses penyalinan (backup) gagal karena error, gunakan `try-except` untuk menangkapnya dan pastikan fungsi tersebut mengembalikan `return "Error: Gagal melakukan operasi backup sebelum mengedit file."`
7. Biarkan parameter/argumen dan output fungsi yang asli tidak berubah, hanya selipkan langkah backup di tengahnya saja.

### Bagian 3: Instruksi untuk Pembuatan Unit Test Dasar

Tugas Anda adalah membuat kerangka pengujian (testing) untuk aplikasi ini agar kita bisa mengecek fungsionalitas dari file *tools* terbebas dari error.

1. Buat direktori folder baru di root direktori dengan nama `tests/`.
2. Di dalamnya (dalam sub-direktori `tests/`), buat satu file kosong bernama `__init__.py`.
3. Buat file baru lagi di dalam `tests/` bernama `test_file_tools.py`.
4. Deklarasikan `import pytest` di baris pertama `test_file_tools.py`.
5. Deklarasikan impor untuk fungsi yang akan dites: `from tools.file_tools import create_file`.
6. Buat fungsi test dasar bahasa python bernama `def test_create_file_success(tmp_path):`.
7. Di dalam implementasinya, gunakan variabel bawaan pytest (`tmp_path`) sebagai rujukan direktori/folder sementaranya. Panggil modul `create_file` menggunakan rujukan lokasi test di dalam variabel tersebut.
8. Gunakan keyword `assert` yang berlaku di standar Python untuk memastikan apakah konten teks file yang sudah di-*create* isinya tepat persis seperti parameter string yang diberikan pemanggilnya.

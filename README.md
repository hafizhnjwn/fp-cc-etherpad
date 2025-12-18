# Etherpad SaaS - Multi-Tenant Cloud PlatformProyek ini adalah implementasi **Platform-as-a-Service (PaaS)** dan **Software-as-a-Service (SaaS)** menggunakan **Etherpad Lite** sebagai basis aplikasi editor kolaboratif *real-time*. Proyek ini dirancang untuk memenuhi tugas akhir mata kuliah Komputasi Awan, mendemonstrasikan konsep *Multi-tenancy*, *Dynamic Provisioning*, dan *State Isolation* menggunakan Docker.

## 🌟 Fitur Utama1. **Container-based Multi-tenancy:** Setiap tenant (klien) mendapatkan container Etherpad terisolasi sendiri untuk keamanan dan manajemen sumber daya.
2. **Dynamic Provisioning:** Pembuatan instance tenant baru secara otomatis via Dashboard Admin (Python Flask) tanpa mematikan server.
3. **Centralized Database:** Menggunakan satu instance PostgreSQL untuk menyimpan data dari semua tenant secara terpusat.
4. **Global Shared Storage:** Fitur "Smart Link" yang memungkinkan kolaborasi lintas-tenant dengan mempertahankan identitas user dan sesi *real-time*.
5. **Seamless Identity Handover:** Otomatisasi login user antar dashboard manajemen dan editor Etherpad menggunakan injeksi skrip dan parameter URL.

## 🏗️ Arsitektur SistemSistem ini terdiri dari beberapa komponen yang diorkestrasi menggunakan Docker Compose:

* **SaaS Manager (Python Flask - Port 8080):**
* Bertindak sebagai *Orchestrator* dan *Portal Login*.
* Mengelola pengguna, autentikasi, dan registrasi Pad global.
* Berkomunikasi dengan Docker Daemon (`/var/run/docker.sock`) untuk membuat container baru.


* **Etherpad Nodes (Node.js - Dynamic Ports 9001+):**
* Container aplikasi editor yang dibuat sesuai permintaan.
* Terhubung ke database pusat namun memiliki *state* RAM (WebSocket) yang terisolasi.


* **Database (PostgreSQL - Port Host 5433):**
* Penyimpanan persisten untuk semua data pad dan user manajemen.



## 🚀 Panduan Instalasi & MenjalankanIkuti langkah-langkah berikut untuk menjalankan sistem ini dari awal.

### Prasyarat* Docker & Docker Compose terinstall.
* Git.
* Koneksi internet (untuk pull image).

### 1. Persiapan Kode SumberPastikan struktur folder proyek sudah sesuai, termasuk folder `saas_manager` yang berisi kode Python dan modifikasi `docker-compose.yml`.

### 2. Injeksi Skrip Auto-LoginAgar nama user dari Dashboard terbaca otomatis di Etherpad, kita perlu menyuntikkan skrip ke dalam template Etherpad.

Buka file `src/templates/pad.html` dan tambahkan kode berikut tepat sebelum tag `</body>` atau `</html>`:

```html
<script type="text/javascript">
    (function() {
        const urlParams = new URLSearchParams(window.location.search);
        const autoName = urlParams.get('userName');
        if (autoName) {
            const checkEtherpadLoaded = setInterval(function() {
                const nameInput = document.querySelector('#myusernameedit');
                if (nameInput && typeof pad !== 'undefined' && pad.collabClient) {
                    nameInput.value = autoName;
                    pad.collabClient.updateUserInfo({name: autoName});
                    document.querySelector('#myuser').style.display = 'none';
                    clearInterval(checkEtherpadLoaded);
                }
            }, 500);
        }
    })();
</script>

```

### 3. Build Image DasarKita perlu membangun image dasar Etherpad dengan konfigurasi *copy* (bukan git) agar proses build lebih cepat dan stabil.

```bash
docker build -t my-etherpad-saas --build-arg BUILD_ENV=copy .

```

### 4. Jalankan Sistem (Provisioning)Jalankan seluruh infrastruktur menggunakan Docker Compose.

```bash
docker compose up -d --build

```

*Catatan: Jika ada error port conflict pada Postgres, pastikan port host di `docker-compose.yml` sudah diubah ke `5433:5432`.*

## 📖 Panduan Penggunaan###Login Admin1. Buka browser dan akses **`http://localhost:8080`**.
2. Login default:
* **Username:** `admin`
* **Password:** `admin123`



### Menambah Tenant (Provisioning)1. Di Dashboard Admin, isi form "Tambah Tenant Baru".
2. Klik **Deploy**. Sistem akan membuat container baru di port yang tersedia (misal: 9001).
3. Container baru akan muncul di daftar "Active Instances".

### Skenario Kolaborasi Real-Time (PENTING)Karena arsitektur *state isolation*, kolaborasi *real-time* hanya terjadi jika user berada di container (port) yang sama.

1. **User A (Port 9001)** membuat dokumen baru bernama `Rapat`.
2. Link akan terdaftar di **Global Shared Storage**.
3. **User B (Port 9002)** login ke dashboard-nya sendiri.
4. User B mengklik link `Rapat` di Global Storage.
5. Sistem secara cerdas mengarahkan User B ke **Port 9001** (Server User A) dengan membawa identitas `?userName=UserB`.
6. User A dan User B bertemu di satu server, fitur *highlight* warna dan kursor *real-time* aktif.

## 🛠️ Teknologi yang Digunakan* **Frontend/Backend App:** [Etherpad Lite](https://github.com/ether/etherpad-lite)
* **Orchestration:** Docker Engine API (via Python SDK).
* **Management Dashboard:** Python Flask, SQLAlchemy, Flask-Login.
* **Database:** PostgreSQL 15 (Alpine).

## ⚠️ Troubleshooting* **Error `bind: address already in use`:** Port 9001/9002 mungkin masih dipakai oleh container "hantu" yang tidak terhapus. Jalankan `docker rm -f $(docker ps -a -q)` untuk membersihkan.
* **Etherpad Loading Terus:** Tunggu 15-30 detik setelah container baru dibuat agar Node.js selesai *booting*.
* **Warna User Tidak Muncul:** Pastikan kedua user mengakses URL dengan **Port yang SAMA** (lihat bagian Skenario Kolaborasi).

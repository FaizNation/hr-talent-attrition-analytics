# Fullstack HR MNC Analytics Dashboard

A production-grade fullstack web application for visual analysis and live sub-millisecond querying of the **2,000,000-record HR MNC dataset** stored in MongoDB 8.2.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   MongoDB 8.2 (db_hr_mnc)   |
                      |   - employees (2,000,000)   |
                      |   - 4 Summary Collections   |
                      +-----------------------------+
                                     │
                                     ▼ (Native Driver, O(1) indexed reads)
                      +-----------------------------+
                      |   Backend API (Express.js)  |
                      |   Port: 5001                |
                      +-----------------------------+
                                     │
                                     ▼ JSON REST APIs
                      +-----------------------------+
                      |   Frontend (React 19 + Vite)|
                      |   Port: 5173                |
                      +-----------------------------+
```

- **Database:** MongoDB 8.2 (`db_hr_mnc`) with 2,000,000 documents and secondary indexes.
- **Backend:** Express.js API (`http://localhost:5001`).
- **Frontend:** React 19 + Vite (`http://localhost:5173`).

---

## 2. Quick Startup Guide (2 Langkah Mudah)

Buka 2 jendela terminal / command prompt terpisah:

### Terminal 1: Jalankan Backend Express (Port 5001)
```bash
cd app/backend
npm install
npm start
```
*Output sukses: `[MongoDB] Connected to database: db_hr_mnc` dan `[Express] HR Analytics Backend API listening on http://localhost:5001`.*

### Terminal 2: Jalankan Frontend React Vite (Port 5173)
```bash
cd app/frontend
npm install
npm run dev
```
*Buka browser di: **`http://localhost:5173`**.*

---

## 3. Fitur Utama Dashboard

1. **Top Macro KPI Cards:**
   - Total Headcount: **2.000.000 Karyawan**
   - Total Payroll: **₹3.66 Triliun**
   - Rata-rata Gaji: **₹1.831.290 / tahun**
   - Rata-rata Pengalaman (**7.5 tahun**) & Rating Kinerja (**★ 3.0 / 5**).
   - Sebaran status: Active (70%), Resigned (20%), dll.

2. **Live 2-Million Employee Search Engine:**
   - Kolom pencarian instan untuk ID karyawan apa pun dari `EMP0000001` hingga `EMP2000000`.
   - Tombol demo cepat: `[EMP0000001]`, `[EMP0500000]`, `[EMP1000000]`, `[EMP1500000]`, `[EMP2000000]`.
   - Menampilkan kartu profil lengkap karyawan (Nama, Jabatan, Departemen, Gaji, Status, Work Mode, Pengalaman, Tanggal Masuk, dan Lokasi).
   - **Indikator Latensi Real-Time:** Menampilkan waktu pencarian database (misal: *O(1) Index Lookup: 3.2 ms*).

3. **Distribusi 7 Departemen:**
   - Visual progress bar dan persentase pangsa headcount per divisi (IT, Finance, Sales, HR, Marketing, Operations, R&D).

4. **Komparasi Work Mode:**
   - Perbandingan On-site vs Remote (jumlah karyawan, rata-rata gaji, dan rating kinerja).

5. **Tabel Interaktif 29 Jabatan (Job Titles):**
   - Filter pencarian instan per jabatan atau departemen dengan statistik rentang gaji (min, rata-rata, max).

---

## 4. Panduan Demo di Depan Dosen

1. Tunjukkan kartu ringkasan di bagian atas bahwa sistem membaca data makro dari **2.000.000 karyawan**.
2. Buktikan pencarian data baris ke-1 juta:
   - Klik tombol demo **`[EMP1000000]`** atau ketik `EMP1000000` di kolom pencarian.
   - Perlihatkan bahwa data karyawan baris ke-1 juta muncul instan dalam **3-5 milidetik**.
3. Buka **MongoDB Compass** di layar berdampingan untuk menunjukkan bahwa datanya sinkron 100% dengan database `db_hr_mnc`.

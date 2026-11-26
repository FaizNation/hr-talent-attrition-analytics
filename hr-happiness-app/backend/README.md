# EHI Backend (Flask)

Backend untuk Employee Happiness Index yang menyajikan model hasil notebook Colab.

## Install & jalankan

```bash
cd hr-happiness-app/backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Server berjalan di `http://localhost:5000` (default).

Letakkan dua file hasil ekspor Colab di `backend/artifacts/`:

- `happiness_model.joblib`
- `dashboard_happiness_summary.json`

> Pastikan versi `scikit-learn` di sini sama dengan di Colab. Cek dengan
> `python -c "import sklearn; print(sklearn.__version__)"` di kedua lingkungan.
> Versi yang di-pin di `requirements.txt` adalah 1.6.1.
>
> Model di-export dari NumPy 2.x, jadi backend juga memakai NumPy 2.x. Untuk
> Python 3.10, versi tertinggi yang tersedia adalah 2.2.6 (sudah di-pin di sini).
> Jika Colab memakai 2.4.x dan ingin versi persis sama, gunakan Python 3.11+ secara lokal.

## Konfigurasi environment

| Variable | Default | Keterangan |
| --- | --- | --- |
| `PORT` | `5000` | Port server |
| `EHI_ARTIFACT_DIR` | `backend/artifacts` | Folder berisi kedua artifact |
| `EHI_CORS_ORIGINS` | `http://localhost:5173` | Origin yang diizinkan, pisahkan dengan koma |

Contoh:

```bash
PORT=5001 EHI_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 python app.py
```

## Endpoint

```bash
# Health
curl http://localhost:5000/api/health

# Opsi departemen dan job title
curl http://localhost:5000/api/options

# Ringkasan dashboard
curl http://localhost:5000/api/summary

# Prediksi
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"department":"Engineering","job_title":"Engineer","salary_inr":1200000,"experience_years":3,"tenure_years":2}'
```

Respons prediksi berisi `label`, `label_code`, `probabilities`, `features` (6 fitur
sesuai urutan `feature_names`), dan `warnings` bila role atau experience tidak
ditemukan di data latih sehingga memakai rata-rata gaji global.

## Test

```bash
python -m pytest -q
```

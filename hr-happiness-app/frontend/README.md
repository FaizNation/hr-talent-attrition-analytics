# EHI Frontend

UI Employee Happiness Index HR MNC (React + TypeScript + Vite).

```bash
npm install
cp .env.example .env       # Windows: copy .env.example .env
npm run dev                # http://localhost:5173
```

Isi `VITE_API_URL` di `.env` dengan base URL backend Flask (default
`http://localhost:5000`). Backend harus berjalan sebelum halaman dimuat.

Halaman: Dashboard (`/`), Analisis Resign (`/resign`), Simulasi (`/simulasi`),
Evaluasi Model (`/model`).

```bash
npm run build   # type-check + build produksi
npm run lint
```

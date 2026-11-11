const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://localhost:5001/api';

export async function fetchOverview() {
  const res = await fetch(`${API_BASE}/overview`);
  if (!res.ok) throw new Error('Failed to load overview data');
  return res.json();
}

export async function fetchDepartments() {
  const res = await fetch(`${API_BASE}/departments`);
  if (!res.ok) throw new Error('Failed to load departments');
  return res.json();
}

export async function fetchJobTitles() {
  const res = await fetch(`${API_BASE}/job-titles`);
  if (!res.ok) throw new Error('Failed to load job titles');
  return res.json();
}

export async function fetchWorkModes() {
  const res = await fetch(`${API_BASE}/work-modes`);
  if (!res.ok) throw new Error('Failed to load work modes');
  return res.json();
}

export async function fetchEmployeeById(id) {
  const res = await fetch(`${API_BASE}/employees/${encodeURIComponent(id)}`);
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Karyawan dengan ID '${id}' tidak ditemukan`);
    }
    throw new Error('Gagal mengambil data karyawan');
  }
  return res.json();
}

export function Skeleton({ className = '', rows = 1 }: { className?: string; rows?: number }) {
  return (
    <div className={className} aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <span key={index} className="skeleton" style={{ animationDelay: `${index * 90}ms` }} />
      ))}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <div>
        <p className="eyebrow">Gagal memuat data</p>
        <p>{message}</p>
      </div>
      <button type="button" className="button ghost" onClick={onRetry}>
        Coba lagi
      </button>
    </div>
  )
}

export function Disclaimer() {
  return (
    <aside className="disclaimer">
      <span className="eyebrow">Catatan metodologi</span>
      <p>
        Skor kebahagiaan adalah estimasi berbasis gaji dan masa kerja (rumus indeks),
        bukan hasil survei kepuasan karyawan.
      </p>
    </aside>
  )
}

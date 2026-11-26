import { useCallback, useEffect, useState } from 'react'
import { getHealth } from './api/client'
import { Navbar } from './components/Navbar'
import { useFetch } from './hooks/useFetch'
import { Dashboard } from './pages/Dashboard'
import { Model } from './pages/Model'
import { Resign } from './pages/Resign'
import { Simulasi } from './pages/Simulasi'

const ROUTES = ['/', '/resign', '/simulasi', '/model']

function currentPath() {
  return ROUTES.includes(window.location.pathname) ? window.location.pathname : '/'
}

export default function App() {
  const [path, setPath] = useState(currentPath)

  useEffect(() => {
    const onPopState = () => setPath(currentPath())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = useCallback((next: string) => {
    window.history.pushState({}, '', next)
    setPath(next)
    window.scrollTo({ top: 0 })
  }, [])

  const healthFetcher = useCallback(() => getHealth(), [])
  const { data: health } = useFetch(healthFetcher)

  return (
    <div className="app-shell">
      <Navbar path={path} model={health?.model} onNavigate={navigate} />
      <main className="page" key={path}>
        {path === '/resign' && <Resign />}
        {path === '/simulasi' && <Simulasi />}
        {path === '/model' && <Model />}
        {path === '/' && <Dashboard />}
      </main>
      <footer className="site-footer">
        <span>EHI · Employee Happiness Index</span>
        <span>Analitik internal HR MNC</span>
      </footer>
    </div>
  )
}

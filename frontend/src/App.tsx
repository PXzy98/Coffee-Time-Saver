import { useState } from 'react'

import AppTheme from './theme/AppTheme.tsx'
import SideMenu from './components/SideMenu.tsx'
import Dashboard from './pages/dashboard/dashboard.tsx'

function App(props: { disableCustomTheme?: boolean }) {
  const [count, setCount] = useState(0)

  return (
    <AppTheme {...props}>
      <SideMenu />
      <Dashboard />
    </AppTheme>
  )
}

export default App

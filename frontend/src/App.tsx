import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Box from '@mui/material/Box'

import AppTheme from './theme/AppTheme.tsx'
import SideMenu from './components/SideMenu.tsx'
import Dashboard from './pages/dashboard/dashboard.tsx'
import TodoPage from './pages/todolist/todoPage.tsx'
import ProjectsExplorer from './pages/projects/projectsExplorer.tsx'
import TasksPage from './pages/tasks/tasksPage.tsx'

const mainListItems = [
  { text: 'Dashboard', href:"/", component: <Dashboard /> },
  { text: 'TODO List', href:"/todo", component: <TodoPage /> },
  { text: 'Project Explorer', href:"/projects", component: <ProjectsExplorer /> },
  { text: 'Tasks', href:"/tasks", component: <TasksPage /> },
];


function App(props: { disableCustomTheme?: boolean }) {

  const [disableCustomTheme, setDisableCustomTheme] = useState(false);

  return (
    <BrowserRouter>
      <AppTheme disableCustomTheme={disableCustomTheme}>
        <Box sx={{ display: 'flex', width: '100%' }}>
          <SideMenu onToggleTheme={() => setDisableCustomTheme(prev => !prev)} />
          <Routes>
            {mainListItems.map((item) => (
              <Route key={item.href} path={item.href} element={item.component} />))}
          </Routes>
        </Box>
        
      </AppTheme>
    </BrowserRouter>
  )
}

export default App

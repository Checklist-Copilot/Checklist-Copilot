import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import HomePage from './pages/HomePage'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import EditChecklistPage from './pages/EditChecklistPage'
import UseChecklistPage from './pages/UseChecklistPage'
import AccountPage from './pages/AccountPage'

function App() {
  const router = createBrowserRouter([
    {
      path: '/',
      element: <LandingPage />,
    },
    {
      path: '/register',
      element: <RegisterPage />,
    },
    {
      path: '/login',
      element: <LoginPage />,
    },
    {
      path: '/home',
      element: <HomePage />,
    },
    {
      path: '/account',
      element: <AccountPage />,
    },
    {
      path: '/checklist/edit/:checklist_id',
      element: <EditChecklistPage />,
    },
    {
      path: '/checklist/use/:checklist_id',
      element: <UseChecklistPage />,
    },
  ])

  return <RouterProvider router={router} />
}

export default App

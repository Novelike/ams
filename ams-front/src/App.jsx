import './App.css'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Registration from './pages/Registration'
import AssetList from './pages/AssetList'
import ChatBot from './pages/ChatBot'
import Label from './pages/Label'
import MainLayout from './layouts/MainLayout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="registration" element={<Registration />} />
          <Route path="assets" element={<AssetList />} />
          <Route path="chatbot" element={<ChatBot />} />
          <Route path="labels" element={<Label />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App

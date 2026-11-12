import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ConfigProvider } from './lib/config'
import { Dashboard } from './pages/Dashboard'
import { Presentation } from './pages/Presentation'
import { Runs } from './pages/Runs'

export default function App() {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/runs/:id" element={<Dashboard />} />
          <Route path="/present" element={<Presentation />} />
          <Route path="/present/:id" element={<Presentation />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

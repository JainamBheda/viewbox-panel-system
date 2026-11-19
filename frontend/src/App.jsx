import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AdminLayout from './layouts/AdminLayout'
import MemberLayout from './layouts/MemberLayout'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import MemberHome from './pages/MemberHome'
import MemberSurveys from './pages/MemberSurveys'
import MemberProfile from './pages/MemberProfile'
import MemberReferrals from './pages/MemberReferrals'
import MemberPayouts from './pages/MemberPayouts'
import AdminDashboard from './pages/AdminDashboard'
import AdminRespondents from './pages/AdminRespondents'
import AdminSources from './pages/AdminSources'
import AdminSurveys from './pages/AdminSurveys'
import AdminReferrals from './pages/AdminReferrals'
import AdminImports from './pages/AdminImports'
import AdminMetaLeads from './pages/AdminMetaLeads'
import AdminPayouts from './pages/AdminPayouts'

function Home() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={user.role === 'ADMIN' || user.role === 'OPERATIONS' ? '/admin' : '/member'} replace />
}

export default function App() {
  return <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/member" element={<ProtectedRoute><MemberLayout /></ProtectedRoute>}>
      <Route index element={<MemberHome />} />
      <Route path="surveys" element={<MemberSurveys />} />
      <Route path="profile" element={<MemberProfile />} />
      <Route path="referrals" element={<MemberReferrals />} />
      <Route path="payouts" element={<MemberPayouts />} />
    </Route>
    <Route path="/admin" element={<ProtectedRoute allow={['ADMIN', 'OPERATIONS']}><AdminLayout /></ProtectedRoute>}>
      <Route index element={<AdminDashboard />} />
      <Route path="respondents" element={<AdminRespondents />} />
      <Route path="sources" element={<AdminSources />} />
      <Route path="surveys" element={<AdminSurveys />} />
      <Route path="referrals" element={<AdminReferrals />} />
      <Route path="imports" element={<AdminImports />} />
      <Route path="meta-leads" element={<AdminMetaLeads />} />
      <Route path="payouts" element={<AdminPayouts />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}

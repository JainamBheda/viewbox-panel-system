import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ allow = ['MEMBER'], children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!allow.includes(user.role)) return <Navigate to={user.role === 'ADMIN' || user.role === 'OPERATIONS' ? '/admin' : '/member'} replace />
  return children
}

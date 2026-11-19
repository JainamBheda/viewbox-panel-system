import { createContext, useContext, useMemo, useState } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

function storedUser() {
  try { return JSON.parse(localStorage.getItem('viewbox_user') || 'null') } catch { return null }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(storedUser)

  const requestOtp = async (phone) => {
    const { data } = await api.post('/auth/request-otp', { phone })
    return data
  }

  const verifyOtp = async (phone, otp) => {
    const { data } = await api.post('/auth/verify-otp', { phone, otp })
    localStorage.setItem('viewbox_token', data.access_token)
    const nextUser = { role: data.role, member_id: data.member_id, profile_complete: data.profile_complete, phone }
    localStorage.setItem('viewbox_user', JSON.stringify(nextUser))
    setUser(nextUser)
    return nextUser
  }

  const logout = () => {
    localStorage.removeItem('viewbox_token')
    localStorage.removeItem('viewbox_user')
    setUser(null)
  }

  const value = useMemo(() => ({ user, requestOtp, verifyOtp, logout, isAdmin: user?.role === 'ADMIN' || user?.role === 'OPERATIONS' }), [user])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

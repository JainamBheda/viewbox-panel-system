import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, ClipboardList, FileSpreadsheet, LayoutDashboard, LogOut, Menu, Radio, Users, Wallet, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/respondents', label: 'Respondents', icon: Users },
  { to: '/admin/sources', label: 'Sources', icon: Radio },
  { to: '/admin/surveys', label: 'Surveys', icon: ClipboardList },
  { to: '/admin/referrals', label: 'Referrals', icon: BarChart3 },
  { to: '/admin/imports', label: 'CSV Import', icon: FileSpreadsheet },
  { to: '/admin/meta-leads', label: 'Meta Leads', icon: Radio },
  { to: '/admin/payouts', label: 'Payouts', icon: Wallet },
]

export default function AdminLayout() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const signOut = () => { logout(); navigate('/login') }

  return <div className="min-h-screen bg-slate-50 lg:flex">
    {open && <div className="fixed inset-0 z-20 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-30 w-64 border-r bg-white p-4 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex items-center justify-between px-2 py-3">
        <div><p className="text-lg font-bold text-brand-700">ViewBox</p><p className="text-xs text-slate-500">Concave Insights</p></div>
        <button className="lg:hidden" aria-label="Close menu" onClick={() => setOpen(false)}><X className="h-5 w-5" /></button>
      </div>
      <nav className="mt-6 space-y-1">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
            className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-50'}`}>
            <Icon className="h-4 w-4" />{label}
          </NavLink>
        ))}
      </nav>
      <div className="absolute bottom-4 left-4 right-4 border-t pt-4">
        <div className="mb-2 text-xs text-slate-500">Signed in as <b>{user?.role}</b></div>
        <button className="btn-secondary w-full" onClick={signOut}><LogOut className="h-4 w-4" /> Sign out</button>
      </div>
    </aside>
    <div className="min-w-0 flex-1">
      <header className="sticky top-0 z-10 flex items-center gap-3 border-b bg-white px-4 py-3 lg:px-8">
        <button className="lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}><Menu className="h-6 w-6" /></button>
        <div><h1 className="text-base font-semibold">Operations Panel</h1><p className="text-xs text-slate-500">Manage panel operations</p></div>
      </header>
      <main className="mx-auto max-w-7xl p-4 lg:p-8"><Outlet /></main>
    </div>
  </div>
}

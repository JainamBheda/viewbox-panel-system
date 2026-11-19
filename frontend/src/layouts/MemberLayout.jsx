import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { ClipboardList, Home, LogOut, RefreshCcw, User, Wallet } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/member', label: 'Home', icon: Home, end: true },
  { to: '/member/surveys', label: 'Surveys', icon: ClipboardList },
  { to: '/member/referrals', label: 'Referrals', icon: RefreshCcw },
  { to: '/member/profile', label: 'Profile', icon: User },
  { to: '/member/payouts', label: 'Wallet', icon: Wallet },
]

export default function MemberLayout() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const signOut = () => { logout(); navigate('/login') }

  return <div className="min-h-screen bg-slate-50 pb-20 md:pb-0">
    <header className="sticky top-0 z-10 border-b bg-white px-4 py-3 md:px-8">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div><p className="text-lg font-bold text-brand-700">ViewBox</p><p className="text-xs text-slate-500">Respondent portal</p></div>
        <button className="btn-secondary !px-3 !py-2" onClick={signOut}><LogOut className="h-4 w-4" /><span className="hidden sm:inline">Sign out</span></button>
      </div>
    </header>
    <main className="mx-auto max-w-5xl p-4 md:p-8"><Outlet /></main>
    <nav className="fixed bottom-0 left-0 right-0 z-20 flex border-t bg-white md:hidden">
      {links.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} className={({ isActive }) => `flex flex-1 flex-col items-center gap-1 py-2 text-[10px] font-medium ${isActive ? 'text-brand-600' : 'text-slate-500'}`}>
          <Icon className="h-5 w-5" />{label}
        </NavLink>
      ))}
    </nav>
    <nav className="hidden md:block">
      <div className="mx-auto flex max-w-5xl gap-1 px-4 pb-6">
        {links.map(({ to, label, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600'}`}>{label}</NavLink>
        ))}
      </div>
    </nav>
  </div>
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FileSpreadsheet, Radio, Users } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { ErrorState, Spinner, StatCard } from '../components/ui'

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const load = () => Promise.all([
    api.get('/admin/dashboard/sources'), api.get('/admin/members?page_size=1'), api.get('/admin/referrals'),
  ]).then(([sources, members, referrals]) => setStats({
    sources: sources.data, total: members.data.total, referrals: referrals.data,
  })).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  if (error) return <ErrorState message={error} retry={load} />
  if (!stats) return <Spinner />
  const signups = stats.sources.reduce((sum, s) => sum + s.signups, 0)
  const fits = stats.sources.reduce((sum, s) => sum + s.fit, 0)
  const completed = stats.sources.reduce((sum, s) => sum + s.completed, 0)

  return <div className="space-y-6">
    <div><h1 className="text-2xl font-bold">Operations dashboard</h1><p className="text-sm text-slate-500">Live, database-backed panel metrics.</p></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Respondents" value={stats.total} icon={Users} />
      <StatCard label="Source signups" value={signups} icon={Radio} />
      <StatCard label="Fit referrals" value={fits} />
      <StatCard label="Completed referrals" value={completed} />
    </div>
    <div className="card">
      <h2 className="text-lg font-semibold">Source performance</h2>
      <p className="mb-4 text-xs text-slate-500">Signups, fit and completed counts per source.</p>
      {stats.sources.length === 0 ? <p className="py-10 text-center text-sm text-slate-500">No sources yet.</p> :
        <div className="h-72"><ResponsiveContainer width="100%" height="100%">
          <BarChart data={stats.sources} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="source" fontSize={11} interval={0} angle={-20} textAnchor="end" height={70} />
            <YAxis allowDecimals={false} fontSize={11} /><Tooltip /><Bar dataKey="signups" fill="#2b76f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="fit" fill="#f59e0b" radius={[4, 4, 0, 0]} /><Bar dataKey="completed" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer></div>}
    </div>
    <div className="grid gap-4 md:grid-cols-3">
      <Link to="/admin/respondents" className="card hover:border-brand-300"><Users className="h-5 w-5 text-brand-600" /><p className="mt-2 font-semibold">Respondent grid</p><p className="text-xs text-slate-500">Search, filter, paginate and export.</p></Link>
      <Link to="/admin/imports" className="card hover:border-brand-300"><FileSpreadsheet className="h-5 w-5 text-brand-600" /><p className="mt-2 font-semibold">CSV import</p><p className="text-xs text-slate-500">Preview messy data before committing.</p></Link>
      <Link to="/admin/surveys" className="card hover:border-brand-300"><Radio className="h-5 w-5 text-brand-600" /><p className="mt-2 font-semibold">Survey administration</p><p className="text-xs text-slate-500">Rules, strict/flexible and applicants.</p></Link>
    </div>
  </div>
}

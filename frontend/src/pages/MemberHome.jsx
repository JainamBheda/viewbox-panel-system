import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, Copy, Gift, Sparkles, Wallet } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Badge, EmptyState, ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function MemberHome() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const { toast } = useToast()

  const load = () => Promise.all([
    api.get('/members/me'), api.get('/members/me/surveys'), api.get('/members/me/referrals'), api.get('/members/me/referral-link'),
  ]).then(([profile, surveys, referrals, link]) => setData({
    profile: profile.data, surveys: surveys.data, referrals: referrals.data, link: link.data,
  })).catch((e) => setError(errorMessage(e)))

  useEffect(() => { load() }, [])

  if (error) return <ErrorState message={error} retry={load} />
  if (!data) return <Spinner />

  const approved = data.surveys.filter((item) => item.eligibility.status === 'APPROVED').length
  const coolOff = data.surveys.find((item) => item.eligibility.reason.includes('Eligible again on'))

  return <div className="space-y-6">
    <div className="rounded-2xl bg-gradient-to-br from-brand-700 to-brand-500 p-6 text-white">
      <p className="text-sm opacity-80">Welcome back</p>
      <h1 className="mt-1 text-2xl font-bold">{data.profile.name}</h1>
      <p className="mt-1 text-sm opacity-90">Member ID: {data.profile.member_code}</p>
      <div className="mt-5 flex flex-wrap gap-3 text-sm">
        <span className="rounded-lg bg-white/15 px-3 py-2"><b>{approved}</b> survey{approved === 1 ? '' : 's'} available</span>
        <span className="rounded-lg bg-white/15 px-3 py-2"><b>{data.referrals.length}</b> people invited</span>
      </div>
    </div>

    <div className="grid gap-3 sm:grid-cols-3">
      <div className="card"><Sparkles className="h-5 w-5 text-brand-600" /><p className="mt-2 text-xs text-slate-500">Your interests</p><p className="text-sm font-semibold">{(data.profile.interests || []).join(', ') || 'Not set'}</p></div>
      <div className="card"><CalendarDays className="h-5 w-5 text-brand-600" /><p className="mt-2 text-xs text-slate-500">Cool-off</p><p className="text-sm font-semibold">{coolOff ? coolOff.eligibility.reason.split('Eligible again on ')[1] : 'None active'}</p></div>
      <div className="card"><Wallet className="h-5 w-5 text-brand-600" /><p className="mt-2 text-xs text-slate-500">Last completed</p><p className="text-sm font-semibold">{data.profile.last_survey_completed_at ? new Date(data.profile.last_survey_completed_at).toLocaleDateString('en-IN') : '—'}</p></div>
    </div>

    <section>
      <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Surveys for you</h2><Link className="text-sm font-semibold text-brand-600" to="/member/surveys">View all</Link></div>
      {data.surveys.length === 0 ? <EmptyState title="No live surveys" message="Check back soon — new surveys are added regularly." /> :
        <div className="grid gap-3 md:grid-cols-2">
          {data.surveys.slice(0, 4).map(({ survey, eligibility }) => <div key={survey.id} className="card">
            <div className="flex items-start justify-between gap-2"><h3 className="font-semibold">{survey.title}</h3><StatusBadge status={eligibility.status} /></div>
            <p className="mt-1 text-sm text-slate-500">{survey.description}</p>
            <p className="mt-3 text-xs text-slate-500">Reward: ₹{survey.reward_amount} · Deadline: {survey.deadline}</p>
            <p className={`mt-2 text-sm ${eligibility.status === 'APPROVED' ? 'text-emerald-700' : 'text-amber-700'}`}>{eligibility.reason}</p>
          </div>)}
        </div>}
    </section>

    <section className="card">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="text-lg font-semibold">Your referral link</h2><p className="mt-1 text-sm text-slate-500">Share this link with people you invite.</p></div>
        <Gift className="h-6 w-6 text-brand-600" />
      </div>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <input readOnly value={`${window.location.origin}/register?ref=${data.link.token}`} className="bg-slate-50 text-xs" aria-label="Referral link" />
        <button className="btn-secondary shrink-0" onClick={async () => {
          await navigator.clipboard?.writeText(`${window.location.origin}/register?ref=${data.link.token}`)
          toast('Referral link copied')
        }}><Copy className="h-4 w-4" /> Copy</button>
      </div>
      <div className="mt-4"><Badge tone="blue">{data.referrals.filter((r) => r.status === 'COMPLETED').length} completed referrals</Badge></div>
    </section>
  </div>
}

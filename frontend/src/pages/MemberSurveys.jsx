import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function MemberSurveys() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const { toast } = useToast()
  const load = () => api.get('/members/me/surveys').then(({ data }) => setItems(data)).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const apply = async (surveyId) => {
    try {
      const { data } = await api.post(`/members/me/surveys/${surveyId}/apply`)
      toast(`Application: ${data.status}. ${data.reason}`, data.status === 'REJECTED' ? 'error' : 'success')
      load()
    } catch (e) { toast(errorMessage(e), 'error') }
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />
  return <div>
    <h1 className="text-2xl font-bold">Available surveys</h1>
    <p className="mt-1 text-sm text-slate-500">Eligibility is evaluated from your profile, survey rules, quota and cool-off period.</p>
    <div className="mt-6 space-y-3">
      {items.length === 0 && <EmptyState title="No live surveys right now" />}
      {items.map(({ survey, eligibility, application_status, has_questionnaire }) => <div key={survey.id} className="card">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div><h2 className="text-lg font-semibold">{survey.title}</h2><p className="text-sm text-slate-500">{survey.description}</p></div>
          <StatusBadge status={eligibility.status} />
        </div>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
          <p>Reward: <b>₹{survey.reward_amount}</b></p><p>Deadline: <b>{survey.deadline}</b></p>
          <p>Quota: <b>{survey.quota}</b></p>
        </div>
        <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">{eligibility.reason}</p>
        {eligibility.rule_results?.length > 0 && <ul className="mt-3 space-y-1 text-xs text-slate-500">
          {eligibility.rule_results.map((rule) => <li key={rule.rule_id}>{rule.passed ? '✓' : '✕'} {rule.label} ({rule.rule_type})</li>)}
        </ul>}
        <div className="mt-4 flex items-center gap-3">
          <button className="btn-primary" disabled={eligibility.status !== 'APPROVED'} onClick={() => apply(survey.id)}>Apply now</button>
          {application_status === 'APPROVED' && has_questionnaire && <a className="btn-secondary"
            href={`/member/surveys/${survey.id}/respond`}>Open questionnaire</a>}
          {application_status && <span className="text-xs text-slate-500">Saved decision: {application_status}</span>}
        </div>
      </div>)}
    </div>
  </div>
}

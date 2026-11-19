import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Field, Modal, Spinner, StatusBadge } from '../components/ui'

const blank = { title: '', description: '', deadline: '', quota: 100, reward_amount: 100, status: 'LIVE',
  rules: [{ field_name: 'age', operator: 'GTE', expected_value: '18', rule_type: 'STRICT' }] }

export default function AdminSurveys() {
  const [surveys, setSurveys] = useState(null)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(blank)
  const [applicants, setApplicants] = useState(null)
  const [error, setError] = useState('')
  const { toast } = useToast()

  const load = () => api.get('/admin/surveys').then(({ data }) => { setSurveys(data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const create = async (event) => {
    event.preventDefault()
    try {
      await api.post('/admin/surveys', { ...form, deadline: form.deadline, quota: Number(form.quota), reward_amount: Number(form.reward_amount) })
      toast('Survey created and decisions calculated'); setOpen(false); setForm(blank); load()
    } catch (e) { toast(errorMessage(e), 'error') }
  }
  const viewApplicants = async (id) => {
    try { const { data } = await api.get(`/admin/surveys/${id}/applications`); setApplicants(data) }
    catch (e) { toast(errorMessage(e), 'error') }
  }
  const complete = async (surveyId, memberId) => {
    try { await api.post(`/admin/surveys/${surveyId}/completions/${memberId}`, { quality_status: 'PASSED' }); toast('Completion recorded, cool-off started', 'success'); viewApplicants(surveyId) }
    catch (e) { toast(errorMessage(e), 'error') }
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!surveys) return <Spinner />
  return <div>
    <div className="flex items-center justify-between"><div><h1 className="text-2xl font-bold">Survey administration</h1>
      <p className="text-sm text-slate-500">Create surveys, configure strict/flexible rules and review decisions.</p></div>
      <button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New survey</button></div>
    <div className="mt-6 space-y-4">
      {surveys.length === 0 && <EmptyState title="No surveys yet" />}
      {surveys.map((survey) => <div key={survey.id} className="card">
        <div className="flex flex-wrap items-start justify-between gap-2"><div><h2 className="text-lg font-semibold">{survey.title}</h2>
          <p className="text-sm text-slate-500">{survey.description}</p></div><StatusBadge status={survey.status} /></div>
        <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
          <p>Deadline: <b>{survey.deadline}</b></p><p>Quota: <b>{survey.quota}</b></p><p>Reward: <b>₹{survey.reward_amount}</b></p>
          <p>Rules: <b>{survey.rules.length}</b></p>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">{survey.rules.map((rule) => <span key={rule.id} className="badge bg-slate-100 text-slate-700">
          {rule.field_name} {rule.operator} {rule.expected_value} · {rule.rule_type}</span>)}</div>
        <button className="btn-secondary mt-4" onClick={() => viewApplicants(survey.id)}>View applicants</button>
      </div>)}
    </div>
    <Modal open={open} onClose={() => setOpen(false)} title="Create survey" footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary" onClick={create}>Create survey</button></>}>
      <form onSubmit={create} className="grid gap-4">
        <Field label="Title"><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></Field>
        <Field label="Description"><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Deadline"><input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} required /></Field>
          <Field label="Quota"><input type="number" min="1" value={form.quota} onChange={(e) => setForm({ ...form, quota: e.target.value })} /></Field>
          <Field label="Reward (₹)"><input type="number" min="0" value={form.reward_amount} onChange={(e) => setForm({ ...form, reward_amount: e.target.value })} /></Field>
          <Field label="Status"><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>LIVE</option><option>DRAFT</option><option>CLOSED</option></select></Field>
        </div>
        <div><p className="mb-2 text-sm font-medium">Rules</p>
          {form.rules.map((rule, index) => <div key={index} className="mb-2 grid grid-cols-4 gap-2">
            <select aria-label="Field" value={rule.field_name} onChange={(e) => setForm({ ...form, rules: form.rules.map((r, i) => i === index ? { ...r, field_name: e.target.value } : r) })}>
              {['age', 'city', 'gender', 'income_range', 'interests'].map((f) => <option key={f}>{f}</option>)}</select>
            <select aria-label="Operator" value={rule.operator} onChange={(e) => setForm({ ...form, rules: form.rules.map((r, i) => i === index ? { ...r, operator: e.target.value } : r) })}>
              {['EQ', 'IN', 'GTE', 'LTE', 'CONTAINS'].map((op) => <option key={op}>{op}</option>)}</select>
            <input aria-label="Expected value" value={rule.expected_value} onChange={(e) => setForm({ ...form, rules: form.rules.map((r, i) => i === index ? { ...r, expected_value: e.target.value } : r) })} />
            <select aria-label="Rule type" value={rule.rule_type} onChange={(e) => setForm({ ...form, rules: form.rules.map((r, i) => i === index ? { ...r, rule_type: e.target.value } : r) })}>
              <option>STRICT</option><option>FLEXIBLE</option></select>
          </div>)}
          <button type="button" className="btn-secondary" onClick={() => setForm({ ...form, rules: [...form.rules, { field_name: 'city', operator: 'EQ', expected_value: 'Mumbai', rule_type: 'FLEXIBLE' }] })}>Add rule</button>
        </div>
      </form>
    </Modal>
    <Modal open={applicants !== null} onClose={() => setApplicants(null)} title="Applicants & eligibility decisions">
      {applicants && <div className="space-y-2">{applicants.length === 0 && <EmptyState title="No applications yet" />}
        {applicants.map((item) => <div key={item.id} className="rounded-lg border p-3 text-sm">
          <div className="flex justify-between"><b>Member #{item.member_id}</b><StatusBadge status={item.eligibility_status} /></div>
          <p className="mt-1 text-slate-500">{item.reason}</p>
          <button className="btn-secondary mt-2 !py-1 text-xs" onClick={() => complete(item.survey_id, item.member_id)}>Record PASSED completion</button>
        </div>)}</div>}
    </Modal>
  </div>
}

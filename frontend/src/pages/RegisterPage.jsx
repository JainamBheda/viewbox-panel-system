import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Field } from '../components/ui'

const empty = { name: '', phone: '', email: '', date_of_birth: '', gender: '', city: '', income_range: '', interests: '', how_heard: '' }
const cities = ['Mumbai', 'Navi Mumbai', 'Pune', 'Bengaluru', 'Delhi', 'Hyderabad', 'Ahmedabad', 'Thane', 'Nagpur', 'Nashik']
const incomes = ['Below 3L', '3L-6L', '6L-10L', '10L-20L', 'Above 20L']

export default function RegisterPage() {
  const [params] = useSearchParams()
  const token = params.get('ref')
  const [form, setForm] = useState(empty)
  const [sources, setSources] = useState([])
  const [attribution, setAttribution] = useState(null)
  const [busy, setBusy] = useState(false)
  const { toast } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/public/sources').then(({ data }) => setSources(data)).catch(() => {})
    if (token) api.get('/public/attribution/resolve', { params: { token } }).then(({ data }) => setAttribution(data)).catch(() => {})
  }, [token])

  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      const payload = { ...form, source_token: attribution?.source_id ? token : undefined,
        referral_token: attribution?.referrer_member_id ? token : undefined }
      const { data } = await api.post('/public/register', payload)
      toast(`Registered as ${data.member_code}. Sign in with your phone number.`)
      navigate('/login', { state: { phone: form.phone } })
    } catch (error) { toast(errorMessage(error), 'error') } finally { setBusy(false) }
  }

  return <div className="min-h-screen bg-slate-50 px-4 py-10">
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Join the ViewBox panel</h1>
      <p className="mt-1 text-sm text-slate-500">Tell us a little about yourself. You will earn rewards only for complete, high-quality participation.</p>
      {attribution && <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-800">
        {attribution.source_name && <p>Source: <b>{attribution.source_name}</b></p>}
        {attribution.referrer_member_id && <p>Invited by a member: <b>Yes</b></p>}
        {!attribution.source_name && !attribution.referrer_member_id && <p>We will ask how you heard about us below.</p>}
      </div>}
      <form className="card mt-6 grid gap-4 sm:grid-cols-2" onSubmit={submit}>
        <Field label="Full name"><input aria-label="Full name" value={form.name} onChange={set('name')} required /></Field>
        <Field label="Mobile number"><input aria-label="Mobile number" value={form.phone} onChange={set('phone')} inputMode="numeric" required /></Field>
        <Field label="Email (optional)"><input aria-label="Email (optional)" type="email" value={form.email} onChange={set('email')} /></Field>
        <Field label="Date of birth"><input aria-label="Date of birth" type="date" value={form.date_of_birth} onChange={set('date_of_birth')} required /></Field>
        <Field label="Gender"><select aria-label="Gender" value={form.gender} onChange={set('gender')} required>
          <option value="">Select…</option><option value="MALE">Male</option><option value="FEMALE">Female</option><option value="OTHER">Other</option>
        </select></Field>
        <Field label="City"><select aria-label="City" value={form.city} onChange={set('city')} required>
          <option value="">Select…</option>{cities.map((city) => <option key={city}>{city}</option>)}
        </select></Field>
        <Field label="Income range"><select aria-label="Income range" value={form.income_range} onChange={set('income_range')} required>
          <option value="">Select…</option>{incomes.map((income) => <option key={income}>{income}</option>)}
        </select></Field>
        <Field label="Interests (comma separated)" hint="e.g. Tech, Travel, Food">
          <input aria-label="Interests (comma separated)" value={form.interests} onChange={set('interests')} placeholder="Tech, Travel" /></Field>
        {!attribution?.source_id && <div className="sm:col-span-2"><Field label="How did you hear about us?">
          <select value={form.how_heard} onChange={set('how_heard')}>
            <option value="">Select…</option>{sources.map((source) => <option key={source.id} value={source.name}>{source.name}</option>)}
          </select></Field></div>}
        <div className="sm:col-span-2"><button className="btn-primary w-full" disabled={busy}>Create account</button></div>
      </form>
    </div>
  </div>
}

import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Field, Spinner } from '../components/ui'

export default function MemberProfile() {
  const [form, setForm] = useState(null)
  const [busy, setBusy] = useState(false)
  const { toast } = useToast()
  useEffect(() => { api.get('/members/me').then(({ data }) => setForm({
    name: data.name, email: data.email || '', date_of_birth: data.date_of_birth || '',
    gender: data.gender || '', city: data.city || '', income_range: data.income_range || '',
    interests: (data.interests || []).join(', '),
  })).catch((e) => toast(errorMessage(e), 'error')) }, [])

  const save = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      await api.put('/members/me/profile', form)
      toast('Profile updated. Eligibility has been recalculated.')
    } catch (e) { toast(errorMessage(e), 'error') } finally { setBusy(false) }
  }
  if (!form) return <Spinner />

  return <div className="max-w-2xl">
    <h1 className="text-2xl font-bold">My profile</h1>
    <p className="mt-1 text-sm text-slate-500">Keeping this current helps us match you to the right surveys.</p>
    <form className="card mt-6 grid gap-4 sm:grid-cols-2" onSubmit={save}>
      <div className="sm:col-span-2"><Field label="Full name"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field></div>
      <Field label="Date of birth"><input type="date" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} /></Field>
      <Field label="Gender"><select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
        <option value="">Select…</option><option value="MALE">Male</option><option value="FEMALE">Female</option><option value="OTHER">Other</option>
      </select></Field>
      <Field label="City"><input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
      <Field label="Income range"><input value={form.income_range} onChange={(e) => setForm({ ...form, income_range: e.target.value })} /></Field>
      <Field label="Email"><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Interests" hint="Comma separated"><input value={form.interests} onChange={(e) => setForm({ ...form, interests: e.target.value })} /></Field>
      <div className="sm:col-span-2"><button className="btn-primary" disabled={busy}>Save changes</button></div>
    </form>
  </div>
}

import { useEffect, useState } from 'react'
import { Link2, Plus } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Badge, EmptyState, ErrorState, Field, Modal, Spinner } from '../components/ui'

const types = ['WHATSAPP_GROUP', 'STAFF_DM', 'INSTAGRAM', 'FACEBOOK', 'WEBSITE', 'REFERRAL', 'META_ADS', 'OTHER']

export default function AdminSources() {
  const [sources, setSources] = useState(null)
  const [links, setLinks] = useState([])
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', source_type: 'INSTAGRAM', description: '' })
  const [error, setError] = useState('')
  const { toast } = useToast()

  const load = () => Promise.all([api.get('/admin/sources'), api.get('/admin/sources/links')])
    .then(([a, b]) => { setSources(a.data); setLinks(b.data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const create = async (event) => {
    event.preventDefault()
    try { await api.post('/admin/sources', form); toast('Source created with a default link'); setOpen(false); setForm({ name: '', source_type: 'INSTAGRAM', description: '' }); load() }
    catch (e) { toast(errorMessage(e), 'error') }
  }
  const newLink = async (sourceId) => {
    try { await api.post(`/admin/sources/${sourceId}/links`, null, { params: { campaign_name: 'New campaign' } }); toast('Signup link created'); load() }
    catch (e) { toast(errorMessage(e), 'error') }
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!sources) return <Spinner />
  return <div>
    <div className="flex items-center justify-between"><div><h1 className="text-2xl font-bold">Sources &amp; signup links</h1>
      <p className="text-sm text-slate-500">Sources are managed dynamically — never hardcoded.</p></div>
      <button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New source</button></div>
    <div className="mt-6 grid gap-4 lg:grid-cols-2">
      {sources.length === 0 && <EmptyState title="No sources yet" />}
      {sources.map((source) => <div key={source.id} className="card">
        <div className="flex items-start justify-between"><div><h2 className="font-semibold">{source.name}</h2><p className="text-xs text-slate-500">{source.source_type}</p></div>
          <Badge tone={source.is_active ? 'green' : 'red'}>{source.is_active ? 'Active' : 'Inactive'}</Badge></div>
        <p className="mt-2 text-sm text-slate-500">{source.description || 'No description'}</p>
        <button className="btn-secondary mt-4" onClick={() => newLink(source.id)}><Link2 className="h-4 w-4" /> Create signup link</button>
        <div className="mt-3 space-y-1">
          {links.filter((l) => l.source_id === source.id).map((link) => <div key={link.id} className="rounded-lg bg-slate-50 p-2 text-xs">
            <span className="font-mono">{link.token}</span> <span className="text-slate-500">· {link.campaign_name || '—'}</span>
          </div>)}
        </div>
      </div>)}
    </div>
    <Modal open={open} onClose={() => setOpen(false)} title="Create source" footer={<><button className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary" onClick={create}>Create</button></>}>
      <form onSubmit={create} className="grid gap-4">
        <Field label="Source name"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
        <Field label="Type"><select value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
          {types.map((type) => <option key={type}>{type}</option>)}</select></Field>
        <Field label="Description"><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
      </form>
    </Modal>
  </div>
}

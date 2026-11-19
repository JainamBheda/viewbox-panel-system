import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function AdminMetaLeads() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.get('/admin/meta-leads').then(({ data }) => { setItems(data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])
  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />
  return <div>
    <h1 className="text-2xl font-bold">Meta leads</h1><p className="text-sm text-slate-500">Leads received by the mock webhook. Duplicate lead IDs never create a second member.</p>
    <div className="table-wrap mt-6"><table className="table"><thead><tr><th className="th">Lead ID</th><th className="th">Form</th><th className="th">Campaign</th><th className="th">Ad</th><th className="th">Status</th><th className="th">Member</th><th className="th">Notes</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.id} className="border-t"><td className="td font-mono text-xs">{item.meta_lead_id}</td><td className="td">{item.form_id || '—'}</td>
        <td className="td">{item.campaign_id || '—'}</td><td className="td">{item.ad_id || '—'}</td><td className="td"><StatusBadge status={item.processing_status} /></td>
        <td className="td">{item.member_id || '—'}</td><td className="td text-xs text-rose-600">{item.failure_reason || '—'}</td></tr>)}</tbody></table>
      {items.length === 0 && <div className="p-5 text-sm text-slate-500">No leads received yet.</div>}
    </div>
  </div>
}

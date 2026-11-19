import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Field, Modal, Spinner, StatusBadge } from '../components/ui'

export default function AdminReferrals() {
  const [items, setItems] = useState(null)
  const [editing, setEditing] = useState(null)
  const [stage, setStage] = useState('FIT')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const { toast } = useToast()
  const load = () => api.get('/admin/referrals').then(({ data }) => { setItems(data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const save = async () => {
    try {
      await api.patch(`/admin/referrals/${editing.id}/stage`, { status: stage, failure_reason: reason || null })
      toast('Referral stage updated'); setEditing(null); setReason(''); load()
    } catch (e) { toast(errorMessage(e), 'error') }
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />
  return <div>
    <h1 className="text-2xl font-bold">Referrals</h1><p className="text-sm text-slate-500">Move referrals through LEAD → FIT → COMPLETED, or record a failure.</p>
    <div className="table-wrap mt-6">{items.length === 0 ? <div className="p-4"><EmptyState title="No referrals yet" /></div> :
      <table className="table"><thead><tr><th className="th">ID</th><th className="th">Referred member</th><th className="th">Stage</th><th className="th">Failure reason</th><th className="th"></th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id} className="border-t"><td className="td">#{item.id}</td><td className="td">{item.referred_name || '—'}</td>
          <td className="td"><StatusBadge status={item.status} /></td><td className="td text-xs text-rose-600">{item.failure_reason || '—'}</td>
          <td className="td"><button className="text-xs font-semibold text-brand-600" onClick={() => { setEditing(item); setStage(item.status) }}>Update</button></td></tr>)}</tbody></table>}
    </div>
    <Modal open={!!editing} onClose={() => setEditing(null)} title={`Update referral #${editing?.id}`} footer={<><button className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button><button className="btn-primary" onClick={save}>Save</button></>}>
      <div className="grid gap-4"><Field label="Stage"><select value={stage} onChange={(e) => setStage(e.target.value)}>
        {['LEAD', 'FIT', 'COMPLETED', 'FAILED'].map((s) => <option key={s}>{s}</option>)}</select></Field>
        {stage === 'FAILED' && <Field label="Failure reason (visible to referrer)"><textarea value={reason} onChange={(e) => setReason(e.target.value)} required /></Field>}
        {stage === 'COMPLETED' && <p className="text-xs text-slate-500">A PASSED survey completion must already exist for this member.</p>}
      </div>
    </Modal>
  </div>
}

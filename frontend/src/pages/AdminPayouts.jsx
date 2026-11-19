import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function AdminPayouts() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const { user } = useAuth()
  const { toast } = useToast()

  const load = () => api.get('/admin/payouts').then(({ data }) => { setItems(data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const change = async (id, status) => {
    try {
      await api.patch(`/admin/payouts/${id}`, null, { params: { status_value: status } })
      toast(`Payout marked ${status}`)
      load()
    } catch (e) { toast(errorMessage(e), 'error') }
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />

  const total = (status) => items.filter((item) => item.status === status).reduce((sum, item) => sum + Number(item.amount), 0)

  return <div>
    <h1 className="text-2xl font-bold">Payout ledger</h1>
    <p className="mt-1 text-sm text-slate-500">Immutable rows track every reward. Only full admins can approve or mark as paid.</p>
    <div className="mt-6 grid gap-3 sm:grid-cols-3">
      <div className="card"><p className="text-xs text-slate-500">Pending</p><p className="text-2xl font-bold">₹{total('PENDING')}</p></div>
      <div className="card"><p className="text-xs text-slate-500">Approved</p><p className="text-2xl font-bold">₹{total('APPROVED')}</p></div>
      <div className="card"><p className="text-xs text-slate-500">Paid</p><p className="text-2xl font-bold">₹{total('PAID')}</p></div>
    </div>
    <div className="table-wrap mt-6">
      <table className="table">
        <thead><tr><th className="th">ID</th><th className="th">Member</th><th className="th">Source</th><th className="th">Amount</th><th className="th">Status</th><th className="th">Actions</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id} className="border-t">
          <td className="td">#{item.id}</td><td className="td">#{item.member_id}</td><td className="td">{item.source_type}</td>
          <td className="td">₹{item.amount}</td><td className="td"><StatusBadge status={item.status} /></td>
          <td className="td space-x-2">
            {user?.role === 'ADMIN' && item.status === 'PENDING' && <button className="text-xs font-semibold text-brand-600" onClick={() => change(item.id, 'APPROVED')}>Approve</button>}
            {user?.role === 'ADMIN' && item.status === 'APPROVED' && <button className="text-xs font-semibold text-brand-600" onClick={() => change(item.id, 'PAID')}>Mark paid</button>}
            {!['PAID', 'FAILED'].includes(item.status) && <button className="text-xs font-semibold text-rose-600" onClick={() => change(item.id, 'FAILED')}>Fail</button>}
          </td>
        </tr>)}</tbody>
      </table>
      {items.length === 0 && <div className="p-5"><EmptyState title="No payouts yet" message="Payouts appear after completions and completed referrals." /></div>}
    </div>
  </div>
}

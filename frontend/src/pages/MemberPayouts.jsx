import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { EmptyState, ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function MemberPayouts() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.get('/members/me/payouts').then(({ data }) => setItems(data)).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])
  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />
  return <div>
    <h1 className="text-2xl font-bold">Wallet</h1>
    <p className="mt-1 text-sm text-slate-500">Rewards for completed surveys and successful referrals.</p>
    <div className="mt-6 grid gap-3 sm:grid-cols-3">
      <div className="card"><p className="text-xs text-slate-500">Pending</p><p className="text-2xl font-bold">₹{items.filter((i) => i.status === 'PENDING').reduce((s, i) => s + Number(i.amount), 0)}</p></div>
      <div className="card"><p className="text-xs text-slate-500">Approved</p><p className="text-2xl font-bold">₹{items.filter((i) => i.status === 'APPROVED').reduce((s, i) => s + Number(i.amount), 0)}</p></div>
      <div className="card"><p className="text-xs text-slate-500">Paid</p><p className="text-2xl font-bold">₹{items.filter((i) => i.status === 'PAID').reduce((s, i) => s + Number(i.amount), 0)}</p></div>
    </div>
    <div className="table-wrap mt-6">
      <table className="table"><thead><tr><th className="th">Type</th><th className="th">Amount</th><th className="th">Status</th><th className="th">Created</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id} className="border-t"><td className="td">{item.source_type}</td><td className="td">₹{item.amount}</td><td className="td"><StatusBadge status={item.status} /></td><td className="td">{new Date(item.created_at).toLocaleDateString('en-IN')}</td></tr>)}</tbody>
      </table>
      {items.length === 0 && <div className="p-4"><EmptyState title="No payouts yet" /></div>}
    </div>
  </div>
}

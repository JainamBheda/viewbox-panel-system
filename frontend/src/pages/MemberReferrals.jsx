import { useEffect, useState } from 'react'
import { Copy } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Spinner, StatusBadge } from '../components/ui'

export default function MemberReferrals() {
  const [items, setItems] = useState(null)
  const [link, setLink] = useState('')
  const [error, setError] = useState('')
  const { toast } = useToast()
  const load = () => Promise.all([api.get('/members/me/referrals'), api.get('/members/me/referral-link')])
    .then(([a, b]) => { setItems(a.data); setLink(`${window.location.origin}/register?ref=${b.data.token}`) })
    .catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  if (error) return <ErrorState message={error} retry={load} />
  if (!items) return <Spinner />
  return <div>
    <h1 className="text-2xl font-bold">Referrals</h1>
    <p className="mt-1 text-sm text-slate-500">Track the people you invited. Phone numbers are always masked.</p>
    <div className="card mt-5 flex flex-col gap-2 sm:flex-row sm:items-center">
      <input readOnly aria-label="Referral link" value={link} className="bg-slate-50 text-xs" />
      <button className="btn-secondary shrink-0" onClick={async () => { await navigator.clipboard?.writeText(link); toast('Link copied') }}><Copy className="h-4 w-4" /> Copy</button>
    </div>
    <div className="mt-5 space-y-3">
      {items.length === 0 && <EmptyState title="No referrals yet" message="Share your link to invite people." />}
      {items.map((item) => <div key={item.id} className="card flex items-start justify-between gap-4">
        <div><p className="font-semibold">{item.referred_name}</p><p className="text-xs text-slate-500">{item.member_code} · {item.masked_phone}</p>
          {item.failure_reason && <p className="mt-2 text-sm text-rose-600">Reason: {item.failure_reason}</p>}
        </div>
        <StatusBadge status={item.status} />
      </div>)}
    </div>
  </div>
}

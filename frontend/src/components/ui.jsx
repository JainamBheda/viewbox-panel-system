import { AlertTriangle, Loader2, X } from 'lucide-react'

export function Spinner({ label = 'Loading…' }) {
  return <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500"><Loader2 className="h-5 w-5 animate-spin" />{label}</div>
}

export function EmptyState({ title = 'Nothing here yet', message }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
    <p className="font-semibold">{title}</p>
    {message && <p className="mt-1 text-sm text-slate-500">{message}</p>}
  </div>
}

export function ErrorState({ message, retry }) {
  return <div className="flex flex-col items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-6 py-10 text-center">
    <AlertTriangle className="h-6 w-6 text-rose-500" />
    <p className="text-sm text-rose-700">{message}</p>
    {retry && <button className="btn-secondary" onClick={retry}>Try again</button>}
  </div>
}

export function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700', green: 'bg-emerald-100 text-emerald-700',
    amber: 'bg-amber-100 text-amber-700', red: 'bg-rose-100 text-rose-700',
    blue: 'bg-blue-100 text-blue-700',
  }
  return <span className={`badge ${tones[tone] || tones.slate}`}>{children}</span>
}

export function StatusBadge({ status }) {
  const tone = ['APPROVED', 'COMPLETED', 'PAID', 'ACTIVE'].includes(status) ? 'green'
    : ['WAITLISTED', 'PENDING', 'FIT', 'LEAD', 'PREVIEW'].includes(status) ? 'amber'
      : ['REJECTED', 'FAILED', 'FLAGGED'].includes(status) ? 'red' : 'slate'
  return <Badge tone={tone}>{status?.replaceAll('_', ' ')}</Badge>
}

export function StatCard({ label, value, hint, icon: Icon }) {
  return <div className="card flex items-center gap-4">
    {Icon && <div className="rounded-xl bg-brand-50 p-3 text-brand-600"><Icon className="h-6 w-6" /></div>}
    <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  </div>
}

export function Modal({ open, onClose, title, children, footer }) {
  if (!open) return null
  return <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/50 p-4" role="dialog" aria-modal="true">
    <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
      <div className="flex items-center justify-between border-b px-5 py-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <button aria-label="Close" onClick={onClose}><X className="h-5 w-5 text-slate-400" /></button>
      </div>
      <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
      {footer && <div className="flex justify-end gap-2 border-t px-5 py-4">{footer}</div>}
    </div>
  </div>
}

export function Field({ label, children, hint }) {
  return <div><label>{label}</label>{children}{hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}</div>
}

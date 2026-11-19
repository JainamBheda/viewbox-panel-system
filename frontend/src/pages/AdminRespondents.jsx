import { useEffect, useState } from 'react'
import { Download, Search } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { EmptyState, ErrorState, Modal, Spinner, StatusBadge } from '../components/ui'

const blankFilters = { search: '', source_id: '', city: '', status: '' }

export default function AdminRespondents() {
  const [filters, setFilters] = useState(blankFilters)
  const [result, setResult] = useState(null)
  const [sources, setSources] = useState([])
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const { toast } = useToast()

  useEffect(() => { api.get('/admin/sources').then(({ data }) => setSources(data)).catch(() => {}) }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      const params = { page, page_size: 20, ...filters }
      Object.keys(params).forEach((key) => { if (!params[key]) delete params[key] })
      api.get('/admin/members', { params }).then(({ data }) => { setResult(data); setError('') })
        .catch((e) => setError(errorMessage(e)))
    }, 250)
    return () => clearTimeout(timer)
  }, [filters, page])

  const doExport = async (format) => {
    const params = { format, ...filters }
    Object.keys(params).forEach((key) => { if (!params[key]) delete params[key] })
    try {
      const response = await api.get('/admin/members/export', { params, responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([response.data]))
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `respondents.${format}`
      anchor.click()
      URL.revokeObjectURL(url)
      toast(`Exported ${format.toUpperCase()} with current filters`)
    } catch (e) { toast(errorMessage(e), 'error') }
  }

  return <div>
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-bold">Respondents</h1><p className="text-sm text-slate-500">Search and filter the panel. Exports use the same filters.</p></div>
      <div className="flex gap-2"><button className="btn-secondary" onClick={() => doExport('csv')}><Download className="h-4 w-4" /> CSV</button>
        <button className="btn-secondary" onClick={() => doExport('xlsx')}><Download className="h-4 w-4" /> XLSX</button></div>
    </div>
    <div className="card mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input className="pl-9" placeholder="Name, member ID or city" value={filters.search}
          onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setPage(1) }} aria-label="Search respondents" /></div>
      <select aria-label="Filter by source" value={filters.source_id} onChange={(e) => { setFilters({ ...filters, source_id: e.target.value }); setPage(1) }}>
        <option value="">All sources</option>{sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <input aria-label="Filter by city" placeholder="City" value={filters.city} onChange={(e) => { setFilters({ ...filters, city: e.target.value }); setPage(1) }} />
      <select aria-label="Filter by status" value={filters.status} onChange={(e) => { setFilters({ ...filters, status: e.target.value }); setPage(1) }}>
        <option value="">All statuses</option><option>ACTIVE</option><option>FLAGGED</option>
      </select>
    </div>
    <div className="mt-5">
      {error && <ErrorState message={error} retry={() => setPage(page)} />}
      {!result && !error && <Spinner />}
      {result && <>
        <p className="mb-2 text-xs text-slate-500">{result.total} result{result.total === 1 ? '' : 's'} · page {result.page} of {result.pages}</p>
        {result.items.length === 0 ? <EmptyState title="No respondents match" message="Try changing your filters." /> :
          <div className="table-wrap"><table className="table">
            <thead><tr><th className="th">Member ID</th><th className="th">Name</th><th className="th">City</th><th className="th">Source</th><th className="th">Status</th><th className="th"></th></tr></thead>
            <tbody>{result.items.map((m) => <tr key={m.id} className="border-t hover:bg-slate-50">
              <td className="td font-mono text-xs">{m.member_code}</td><td className="td font-medium">{m.name}</td>
              <td className="td">{m.city || '—'}</td><td className="td">{m.source_id ? sources.find((s) => s.id === m.source_id)?.name || `#${m.source_id}` : '—'}</td>
              <td className="td"><StatusBadge status={m.status} /></td>
              <td className="td"><button className="text-xs font-semibold text-brand-600" onClick={() => setSelected(m)}>View</button></td>
            </tr>)}</tbody>
          </table></div>}
        {result.pages > 1 && <div className="mt-4 flex justify-center gap-2">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <button className="btn-secondary" disabled={page >= result.pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>}
      </>}
    </div>
    <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.name || ''}>
      {selected && <dl className="grid grid-cols-2 gap-3 text-sm">
        {[['Member ID', selected.member_code], ['City', selected.city], ['Gender', selected.gender],
          ['Income', selected.income_range], ['Email', selected.email], ['Joined', selected.joined_at?.slice(0, 10)],
          ['Interests', (selected.interests || []).join(', ')]].map(([label, value]) => <div key={label}>
          <dt className="text-xs text-slate-500">{label}</dt><dd className="font-medium">{value || '—'}</dd></div>)}
      </dl>}
    </Modal>
  </div>
}

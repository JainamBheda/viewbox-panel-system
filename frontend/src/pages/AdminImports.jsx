import { useEffect, useState } from 'react'
import { Download, Upload } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Badge, ErrorState, Spinner } from '../components/ui'

export default function AdminImports() {
  const [jobs, setJobs] = useState([])
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { toast } = useToast()
  const load = () => api.get('/admin/imports').then(({ data }) => { setJobs(data); setError('') }).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  const upload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy(true)
    try {
      const form = new FormData(); form.append('file', file)
      const { data } = await api.post('/admin/imports/upload', form)
      const { data: detail } = await api.get(`/admin/imports/${data.id}/preview`)
      setPreview(detail); load(); toast('File analysed — review the preview before confirming')
    } catch (e) { toast(errorMessage(e), 'error') } finally { setBusy(false) }
  }
  const showPreview = async (id) => {
    try { setPreview((await api.get(`/admin/imports/${id}/preview`)).data) } catch (e) { toast(errorMessage(e), 'error') }
  }
  const confirm = async () => {
    setBusy(true)
    try { await api.post(`/admin/imports/${preview.job.id}/confirm`); toast('Import confirmed'); const id = preview.job.id; await showPreview(id); load() }
    catch (e) { toast(errorMessage(e), 'error') } finally { setBusy(false) }
  }

  if (error) return <ErrorState message={error} retry={load} />
  return <div>
    <h1 className="text-2xl font-bold">CSV import</h1>
    <p className="mt-1 text-sm text-slate-500">Upload → inspect → preview corrections and errors → confirm. Bad rows never stop valid rows.</p>
    <div className="card mt-6">
      <label className="inline-flex cursor-pointer items-center gap-2 btn-primary"><Upload className="h-4 w-4" /> Choose CSV file
        <input type="file" accept=".csv,text/csv" className="hidden" onChange={upload} /></label>
      {busy && <span className="ml-3 text-sm text-slate-500">Working…</span>}
    </div>
    <div className="table-wrap mt-5"><table className="table"><thead><tr><th className="th">Job</th><th className="th">File</th><th className="th">Rows</th><th className="th">Imported</th><th className="th">Skipped</th><th className="th">Status</th><th className="th">Actions</th></tr></thead>
      <tbody>{jobs.map((job) => <tr key={job.id} className="border-t"><td className="td">#{job.id}</td><td className="td">{job.filename}</td><td className="td">{job.total_rows}</td>
        <td className="td">{job.imported_rows}</td><td className="td">{job.skipped_rows}</td><td className="td"><Badge>{job.status}</Badge></td>
        <td className="td"><button className="text-xs font-semibold text-brand-600" onClick={() => showPreview(job.id)}>Preview</button>
          {' '}<a className="text-xs font-semibold text-brand-600" href={`/api/v1/admin/imports/${job.id}/errors.csv`} target="_blank" rel="noreferrer"><Download className="inline h-3 w-3" /> Errors</a></td></tr>)}</tbody></table>
      {jobs.length === 0 && <div className="p-5 text-sm text-slate-500">No uploads yet.</div>}
    </div>
    {preview && <div className="card mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-semibold">Preview — {preview.job.filename}</h2>
          <p className="text-xs text-slate-500">Total {preview.summary.total_rows} · Valid {preview.summary.valid_rows} · Needs review {preview.summary.needs_review} · Skipped {preview.summary.skipped_rows} · Corrections {preview.summary.corrections}</p></div>
        {preview.job.status === 'PREVIEW' && <button className="btn-primary" disabled={busy} onClick={confirm}>Confirm import</button>}
      </div>
      <div className="table-wrap mt-4"><table className="table"><thead><tr><th className="th">Row</th><th className="th">Name (original)</th><th className="th">Action</th><th className="th">Corrections</th><th className="th">Issues</th></tr></thead>
        <tbody>{preview.rows.map((row) => <tr key={row.row_number} className="border-t align-top"><td className="td">{row.row_number}</td><td className="td">{row.original_data.name || <span className="text-slate-400">blank</span>}</td>
          <td className="td"><Badge tone={row.action === 'IMPORT' ? 'green' : 'red'}>{row.action}</Badge></td>
          <td className="td text-xs">{(row.corrections || []).map((c) => <p key={c}>{c}</p>)}</td>
          <td className="td text-xs text-rose-600">{(row.errors || []).map((e) => <p key={e.code + e.message}>{e.code}: {e.message}</p>)}</td></tr>)}</tbody></table></div>
    </div>}
  </div>
}

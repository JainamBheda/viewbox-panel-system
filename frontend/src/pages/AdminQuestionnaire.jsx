import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, FileCode2, RefreshCcw } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { ErrorState, Spinner, StatCard, StatusBadge } from '../components/ui'

const SAMPLE = `Q1 | single | What is your primary commute mode? | Car | Bike | Walk
Q2 | multi | Which factors matter most? | Price | Safety | Time
Q3 | rating | How satisfied are you? | 1-5
Q4 | nps | How likely are you to recommend this study? | 0-10
Q5 | text | Any suggestions about your {Q1} experience?

SHOW | Q2 | IF | Q1 | EQ | Car
SKIP | Q5 | IF | Q3 | GTE | 4
TERMINATE | IF | Q1 | EQ | Walk | Walkers are out of scope
QUOTA | Q1 | Car | 10`

const detailMessage = (e) => {
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return `${detail.message}: ${(detail.errors || []).map((item) => `line ${item.line}: ${item.message}`).join('; ')}`
  return errorMessage(e)
}

export default function AdminQuestionnaire() {
  const { surveyId } = useParams()
  const { toast } = useToast()
  const gutterRef = useRef(null)
  const textRef = useRef(null)
  const [survey, setSurvey] = useState(null)
  const [text, setText] = useState(SAMPLE)
  const [validation, setValidation] = useState(null)
  const [versions, setVersions] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => Promise.all([
    api.get('/admin/surveys'),
    api.get(`/admin/surveys/${surveyId}/questionnaire/versions`),
    api.get(`/admin/surveys/${surveyId}/analytics`),
  ]).then(([allSurveys, versionList, stats]) => {
    setSurvey(allSurveys.data.find((item) => String(item.id) === String(surveyId)) || null)
    setVersions(versionList.data)
    setAnalytics(stats.data)
    setError('')
  }).catch((e) => setError(detailMessage(e)))
  useEffect(() => { load() }, [surveyId])

  const lines = text.split('\n')
  const focusLine = (line) => {
    const offset = lines.slice(0, line - 1).reduce((total, item) => total + item.length + 1, 0)
    textRef.current?.focus()
    textRef.current?.setSelectionRange(offset, offset + (lines[line - 1]?.length || 0))
  }

  const validate = () => {
    setBusy(true)
    api.post(`/admin/surveys/${surveyId}/questionnaire/validate`, { text })
      .then(({ data }) => setValidation(data))
      .catch((e) => toast(detailMessage(e), 'error'))
      .finally(() => setBusy(false))
  }
  const publish = () => {
    setBusy(true)
    api.post(`/admin/surveys/${surveyId}/questionnaire`, { text })
      .then(({ data }) => {
        setValidation(null)
        toast(`Questionnaire v${data.version} published with ${data.question_count} questions.`)
        load()
      })
      .catch((e) => toast(detailMessage(e), 'error'))
      .finally(() => setBusy(false))
  }

  if (error) return <ErrorState message={error} retry={load} />
  if (!analytics) return <Spinner label="Loading questionnaire…" />

  return <div>
    <Link to="/admin/surveys" className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:underline">
      <ArrowLeft className="h-4 w-4" /> Survey administration
    </Link>
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
      <div><h1 className="text-2xl font-bold">Questionnaire · {survey?.title || `Survey #${surveyId}`}</h1>
        <p className="text-sm text-slate-500">Validate, publish an immutable version and review real completion analytics.</p></div>
      <button className="btn-secondary" onClick={load}><RefreshCcw className="h-4 w-4" /> Refresh</button>
    </div>

    <div className="grid gap-4 lg:grid-cols-5">
      <section className="card lg:col-span-3">
        <div className="flex items-center gap-2"><FileCode2 className="h-5 w-5 text-brand-600" /><h2 className="text-lg font-semibold">Questionnaire source</h2></div>
        <p className="mt-1 text-xs text-slate-500">Pipe-separated text DSL. Blank lines and # comments are ignored. Question ids are stable.</p>
        <div className="mt-3 flex overflow-hidden rounded-lg border border-slate-300">
          <pre ref={gutterRef} aria-hidden="true" className="w-12 shrink-0 select-none overflow-hidden border-r border-slate-200 bg-slate-50 py-2 text-right font-mono text-xs text-slate-400"
            style={{ lineHeight: '1.5rem' }}>{lines.map((_, index) => String(index + 1).padStart(2, ' ')).join('\n')}</pre>
          <textarea ref={textRef} aria-label="Questionnaire source" spellCheck={false} value={text}
            onChange={(event) => { setText(event.target.value); setValidation(null) }}
            onScroll={(event) => { if (gutterRef.current) gutterRef.current.scrollTop = event.currentTarget.scrollTop }}
            className="font-mono text-xs" style={{ lineHeight: '1.5rem', padding: '0.5rem 0.75rem' }} rows={18} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="btn-secondary" disabled={busy} onClick={validate}>Validate</button>
          <button className="btn-primary" disabled={busy} onClick={publish}>Publish new version</button>
        </div>
        {validation && (validation.valid
          ? <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700"><CheckCircle2 className="mr-1 inline h-4 w-4" />Valid · {validation.questions.length} questions, {validation.logic.length} logic rules, {validation.terminations.length} screeners.</p>
          : <div className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert">
            <p className="font-semibold">{validation.errors.length} validation error(s) — nothing was published.</p>
            <ul className="mt-2 space-y-1">
              {validation.errors.map((item, index) => <li key={`${item.line}-${index}`}>
                <button className="font-mono underline" onClick={() => focusLine(item.line)}>Line {item.line}</button>: {item.message} <span className="text-rose-400">({item.code})</span>
              </li>)}
            </ul>
          </div>)}
      </section>

      <div className="space-y-4 lg:col-span-2">
        <section className="card">
          <h2 className="text-lg font-semibold">Version history</h2>
          <div className="table-wrap mt-3">
            <table className="table"><thead><tr><th className="th">Version</th><th className="th">Status</th><th className="th">Questions</th></tr></thead>
              <tbody>{versions.map((version) => <tr key={version.id} className="border-t">
                <td className="td">v{version.version}</td><td className="td"><StatusBadge status={version.status} /></td>
                <td className="td">{version.question_count}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </section>
        <section className="grid grid-cols-2 gap-3">
          <StatCard label="Started" value={analytics.started} />
          <StatCard label="Completed" value={analytics.completed} />
          <StatCard label="In progress" value={analytics.in_progress} />
          <StatCard label="Terminated" value={analytics.terminated} />
        </section>
      </div>
    </div>

    <section className="card mt-4">
      <h2 className="text-lg font-semibold">Drop-off by question</h2>
      <div className="table-wrap mt-3"><table className="table"><thead><tr>
        <th className="th">Question</th><th className="th">Reached</th><th className="th">Answered</th><th className="th">Drop-off</th>
      </tr></thead><tbody>
        {analytics.questions.map((item) => <tr key={item.id} className="border-t">
          <td className="td"><span className="font-mono text-xs text-slate-500">{item.id}</span> {item.text}</td>
          <td className="td">{item.reached}</td><td className="td">{item.answered}</td><td className="td">{item.dropoff}</td>
        </tr>)}
        {analytics.questions.length === 0 && <tr><td className="td text-slate-500" colSpan={4}>Publish a questionnaire to see drop-off.</td></tr>}
      </tbody></table></div>
    </section>
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <section className="card"><h2 className="text-lg font-semibold">Termination reasons</h2>
        <ul className="mt-3 space-y-2 text-sm">{analytics.termination_reasons.length === 0 && <li className="text-slate-500">No screen-outs yet.</li>}
          {analytics.termination_reasons.map((item) => <li key={item.reason} className="flex justify-between gap-3"><span>{item.reason}</span><b>{item.count}</b></li>)}
        </ul>
      </section>
      <section className="card"><h2 className="text-lg font-semibold">Quality</h2>
        <p className="mt-3 text-sm text-slate-600">Speeders detected: <b>{analytics.quality_flags.speeders}</b></p>
        <p className="mt-1 text-xs text-slate-500">Computed from completed response duration versus the median; at least {analytics.quality_flags.minimum_completes_for_speeder_check} completes are required before flagging.</p>
      </section>
    </div>
  </div>
}

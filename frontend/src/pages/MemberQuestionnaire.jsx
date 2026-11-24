import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CheckCircle2, ClipboardList } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { ErrorState, Spinner, StatusBadge } from '../components/ui'

const endpoint = (surveyId) => `/members/me/surveys/${surveyId}/response`

function AnswerInput({ question, value, onChange }) {
  const name = `answer-${question.id}`
  if (question.type === 'single' || question.type === 'yesno') {
    return <div role="group" aria-label={question.text} className="grid gap-2 sm:grid-cols-2">
      {(question.options || []).map((option) => <label key={option} htmlFor={`${name}-${option}`}
        className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm hover:border-brand-300">
        <input id={`${name}-${option}`} type="radio" name={name} checked={value === option}
          onChange={() => onChange(option)} className="h-4 w-4 accent-brand-600" />{option}
      </label>)}
    </div>
  }
  if (question.type === 'multi') {
    const selected = Array.isArray(value) ? value : []
    return <div role="group" aria-label={question.text} className="grid gap-2 sm:grid-cols-2">
      {(question.options || []).map((option) => <label key={option} htmlFor={`${name}-${option}`}
        className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm hover:border-brand-300">
        <input id={`${name}-${option}`} type="checkbox" checked={selected.includes(option)}
          onChange={(event) => onChange(event.target.checked ? [...selected, option] : selected.filter((item) => item !== option))}
          className="h-4 w-4 accent-brand-600" />{option}
      </label>)}
    </div>
  }
  if (question.type === 'rating' || question.type === 'nps') {
    const values = Array.from({ length: Number(question.max) - Number(question.min) + 1 }, (_, index) => Number(question.min) + index)
    return <div role="group" aria-label={question.text} className="flex flex-wrap gap-2">
      {values.map((option) => <button key={option} type="button" aria-pressed={value === option}
        onClick={() => onChange(option)}
        className={`h-11 w-11 rounded-xl border text-sm font-semibold transition ${value === option ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-brand-300'}`}>
        {option}
      </button>)}
    </div>
  }
  if (question.type === 'date') {
    return <input id={name} type="date" value={value || ''} onChange={(event) => onChange(event.target.value)} />
  }
  return <textarea id={name} rows={4} maxLength={2000} value={value || ''}
    onChange={(event) => onChange(event.target.value)} placeholder="Type your answer…" />
}

export default function MemberQuestionnaire() {
  const { surveyId } = useParams()
  const { toast } = useToast()
  const [step, setStep] = useState(undefined)
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setStep(undefined)
    api.get(endpoint(surveyId)).then(({ data }) => setStep(data)).catch((e) => {
      if (e?.response?.status === 404) setStep(null)
      else setError(errorMessage(e))
    })
  }, [surveyId])

  useEffect(() => {
    setAnswer(null)
  }, [step?.question?.id, step?.response_id])

  const run = (promise, successMessage) => {
    setBusy(true)
    promise.then(({ data }) => {
      setStep(data)
      setError('')
      if (successMessage && data.status !== 'IN_PROGRESS') successMessage(data)
    }).catch((e) => { toast(errorMessage(e), 'error') }).finally(() => setBusy(false))
  }

  const start = () => run(api.post(`${endpoint(surveyId)}/start`))
  const submit = (event) => {
    event.preventDefault()
    if (answer === null || answer === '' || (Array.isArray(answer) && answer.length === 0)) return
    run(api.post(`${endpoint(surveyId)}/answer`, { question_id: step.question.id, value: answer }),
      (data) => { if (data.status === 'COMPLETED') toast('Response submitted. Thank you!') })
  }
  const back = () => run(api.post(`${endpoint(surveyId)}/back`))

  if (error) return <ErrorState message={error} retry={() => window.location.reload()} />
  if (step === undefined) return <Spinner label="Loading questionnaire…" />

  if (step === null) return <div className="card mx-auto max-w-2xl text-center">
    <ClipboardList className="mx-auto h-10 w-10 text-brand-600" />
    <h1 className="mt-3 text-xl font-bold">Questionnaire not started</h1>
    <p className="mt-2 text-sm text-slate-500">Start only after your application is approved. Your answers are saved after every question.</p>
    <button className="btn-primary mt-5" disabled={busy} onClick={start}>Start questionnaire <ArrowRight className="h-4 w-4" /></button>
    <div className="mt-4"><Link className="text-sm font-medium text-brand-600 hover:underline" to="/member/surveys">Back to surveys</Link></div>
  </div>

  if (step.status !== 'IN_PROGRESS' || !step.question) {
    const done = step.status === 'COMPLETED'
    return <div className="card mx-auto max-w-2xl text-center">
      {done ? <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-600" /> : <ClipboardList className="mx-auto h-10 w-10 text-amber-600" />}
      <h1 className="mt-3 text-xl font-bold">{done ? 'Response submitted' : 'Survey closed for you'}</h1>
      <p className="mt-2 text-sm text-slate-600">{done ? 'Your completion, reward ledger and 3-month cool-off have been recorded.' : step.termination_reason}</p>
      <div className="mt-4"><StatusBadge status={step.status} /></div>
      <div className="mt-5"><Link className="btn-primary" to="/member/surveys"><ArrowLeft className="h-4 w-4" /> Back to surveys</Link></div>
    </div>
  }

  return <div className="mx-auto max-w-2xl">
    <div className="flex items-center justify-between"><div>
      <h1 className="text-2xl font-bold">Questionnaire</h1>
      <p className="text-sm text-slate-500">Version {step.version} · answers autosave as you go</p>
    </div><StatusBadge status={step.status} /></div>

    <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={step.progress} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${step.progress}%` }} />
    </div>
    <p className="mt-1 text-right text-xs text-slate-500">{step.progress}% complete</p>

    <form className="card mt-4" onSubmit={submit} aria-labelledby={`label-${step.question.id}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{step.question.id} · {step.question.type}</p>
      <h2 className="mt-1 text-lg font-semibold" id={`label-${step.question.id}`}>{step.question.text}</h2>
      <div className="mt-4"><AnswerInput question={step.question} value={answer} onChange={setAnswer} /></div>
      <div aria-live="polite" className="mt-6 flex items-center justify-between gap-3">
        <button type="button" className="btn-secondary" disabled={busy} onClick={back}><ArrowLeft className="h-4 w-4" /> Back</button>
        <button type="submit" className="btn-primary" disabled={busy || answer === null || answer === '' || (Array.isArray(answer) && answer.length === 0)}>
          {step.progress >= 100 ? 'Submit' : 'Save & next'} <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </form>
  </div>
}

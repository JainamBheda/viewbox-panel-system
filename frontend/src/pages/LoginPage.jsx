import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ShieldCheck, Smartphone } from 'lucide-react'
import { api, errorMessage } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Field } from '../components/ui'

export default function LoginPage() {
  const [phone, setPhone] = useState('9000000003')
  const [otp, setOtp] = useState('')
  const [devOtp, setDevOtp] = useState('')
  const [step, setStep] = useState('phone')
  const [busy, setBusy] = useState(false)
  const { verifyOtp } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()

  const send = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      const { data } = await api.post('/auth/request-otp', { phone })
      setDevOtp(data.dev_otp || '')
      setStep('otp')
      toast('Verification code sent')
    } catch (error) { toast(errorMessage(error), 'error') } finally { setBusy(false) }
  }

  const verify = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      const user = await verifyOtp(phone, otp)
      toast('Signed in successfully')
      navigate(user.role === 'ADMIN' || user.role === 'OPERATIONS' ? '/admin' : '/member', { replace: true })
    } catch (error) { toast(errorMessage(error), 'error') } finally { setBusy(false) }
  }

  return <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-white to-slate-100 p-4">
    <div className="w-full max-w-md">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white"><ShieldCheck className="h-6 w-6" /></div>
        <h1 className="text-2xl font-bold">ViewBox Panel System</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in with your registered phone number</p>
      </div>
      <div className="card">
        {step === 'phone' ? <form onSubmit={send} className="space-y-4">
          <Field label="Mobile number" hint="Demo member 9000000003 · Admin 9000000001 · Operations 9000000002">
            <div className="relative"><Smartphone className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input className="pl-10" aria-label="Mobile number" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="numeric" required /></div>
          </Field>
          <button className="btn-primary w-full" disabled={busy}>Send OTP <ArrowRight className="h-4 w-4" /></button>
        </form> : <form onSubmit={verify} className="space-y-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <b>Mock OTP:</b> {devOtp || '123456'} <span className="block text-xs">No SMS is sent in this prototype.</span>
          </div>
          <Field label="Enter OTP">
            <input aria-label="Enter OTP" value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" maxLength={6} autoFocus required />
          </Field>
          <button className="btn-primary w-full" disabled={busy}>Verify &amp; continue</button>
          <button type="button" className="btn-secondary w-full" onClick={() => setStep('phone')}>Use a different number</button>
        </form>}
      </div>
      <p className="mt-6 text-center text-sm text-slate-500">New here? <a className="font-semibold text-brand-600" href="/register">Create an account</a></p>
    </div>
  </div>
}

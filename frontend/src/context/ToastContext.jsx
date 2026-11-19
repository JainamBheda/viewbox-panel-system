import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, AlertCircle, X } from 'lucide-react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((items) => [...items, { id, message, type }])
    setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 4500)
  }, [])

  return (
    <ToastContext.Provider value={{ toast: push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-[min(92vw,380px)] flex-col gap-2">
        {toasts.map((item) => (
          <div key={item.id} className={`flex items-start gap-3 rounded-xl border bg-white p-4 shadow-lg ${item.type === 'error' ? 'border-rose-200' : 'border-emerald-200'}`}>
            {item.type === 'error' ? <AlertCircle className="h-5 w-5 text-rose-500" /> : <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
            <p className="flex-1 text-sm">{item.message}</p>
            <button aria-label="Dismiss" onClick={() => setToasts((items) => items.filter((t) => t.id !== item.id))}>
              <X className="h-4 w-4 text-slate-400" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)

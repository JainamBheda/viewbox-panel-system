import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
  errorMessage: vi.fn((error) => error?.message || 'error'),
  toast: vi.fn(),
  verifyOtp: vi.fn(),
}))

vi.mock('../api/client', () => ({ api: mocks.api, errorMessage: mocks.errorMessage }))
vi.mock('../context/ToastContext', () => ({ useToast: () => ({ toast: mocks.toast }) }))
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'MEMBER', member_id: 1 }, verifyOtp: mocks.verifyOtp, isAdmin: false }),
}))

import LoginPage from '../pages/LoginPage'
import RegisterPage from '../pages/RegisterPage'
import MemberSurveys from '../pages/MemberSurveys'
import MemberQuestionnaire from '../pages/MemberQuestionnaire'
import AdminRespondents from '../pages/AdminRespondents'
import AdminQuestionnaire from '../pages/AdminQuestionnaire'
import AdminImports from '../pages/AdminImports'
import ProtectedRoute from '../components/ProtectedRoute'

beforeEach(() => {
  vi.clearAllMocks()
  mocks.api.get.mockResolvedValue({ data: [] })
  mocks.api.post.mockResolvedValue({ data: {} })
  mocks.verifyOtp.mockResolvedValue({ role: 'MEMBER' })
})

describe('member authentication and registration', () => {
  it('requests an OTP, shows the mock code, then verifies it', async () => {
    mocks.api.post.mockImplementation((url) => {
      if (url === '/auth/request-otp') return Promise.resolve({ data: { dev_otp: '123456' } })
      return Promise.resolve({ data: {} })
    })
    render(<MemoryRouter><LoginPage /></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Mobile number'), { target: { value: '9000000003' } })
    fireEvent.click(screen.getByRole('button', { name: /send otp/i }))

    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledWith('/auth/request-otp', { phone: '9000000003' }))
    expect(await screen.findByText(/123456/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Enter OTP'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: /verify/i }))
    await waitFor(() => expect(mocks.verifyOtp).toHaveBeenCalledWith('9000000003', '123456'))
  })

  it('sends both source and referral tokens when a link provides both', async () => {
    mocks.api.get.mockImplementation((url) => {
      if (url === '/public/sources') return Promise.resolve({ data: [{ id: 1, name: 'Instagram' }] })
      if (url === '/public/attribution/resolve') return Promise.resolve({
        data: { source_id: 1, source_name: 'Instagram', referrer_member_id: 7, referral_token: 'REF-X' },
      })
      return Promise.resolve({ data: [] })
    })
    mocks.api.post.mockResolvedValue({ data: { member_code: 'VB99901' } })

    render(<MemoryRouter initialEntries={['/register?ref=SRC-X']}><RegisterPage /></MemoryRouter>)
    expect(await screen.findByText((_, node) => node?.tagName === 'P' && node.textContent === 'Source: Instagram')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test Person' } })
    fireEvent.change(screen.getByLabelText('Mobile number'), { target: { value: '9876543210' } })
    fireEvent.change(screen.getByLabelText('Date of birth'), { target: { value: '1995-06-15' } })
    fireEvent.change(screen.getByLabelText('Gender'), { target: { value: 'FEMALE' } })
    fireEvent.change(screen.getByLabelText('City'), { target: { value: 'Mumbai' } })
    fireEvent.change(screen.getByLabelText('Income range'), { target: { value: '6L-10L' } })
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledWith('/public/register', expect.objectContaining({
      source_token: 'SRC-X', referral_token: 'SRC-X',
    })))
  })
})

describe('member survey decisions', () => {
  it('only allows applying to an approved survey', async () => {
    mocks.api.get.mockResolvedValue({ data: [
      { survey: { id: 11, title: 'Open survey', description: '', deadline: '2026-12-31', quota: 10, reward_amount: 100, rules: [] },
        eligibility: { status: 'APPROVED', reason: 'You match all rules.', rule_results: [] } },
      { survey: { id: 12, title: 'Closed survey', description: '', deadline: '2026-12-31', quota: 10, reward_amount: 100, rules: [] },
        eligibility: { status: 'REJECTED', reason: 'Eligible again on 01-01-2027.', rule_results: [] } },
    ] })

    render(<MemberSurveys />)
    expect(await screen.findByText('Open survey')).toBeInTheDocument()
    expect(screen.getByText('Eligible again on 01-01-2027.')).toBeInTheDocument()

    const buttons = screen.getAllByRole('button', { name: /apply now/i })
    expect(buttons[0]).toBeEnabled()
    expect(buttons[1]).toBeDisabled()
    fireEvent.click(buttons[0])
    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledWith('/members/me/surveys/11/apply'))
  })
})

describe('admin operations', () => {
  it('exports CSV using the active respondent filters', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mocks.api.get.mockImplementation((url) => {
      if (url === '/admin/sources') return Promise.resolve({ data: [{ id: 3, name: 'Instagram' }] })
      if (url === '/admin/members') return Promise.resolve({ data: { items: [], total: 0, page: 1, pages: 1 } })
      if (url === '/admin/members/export') return Promise.resolve({ data: 'member_id,name\n' })
      return Promise.resolve({ data: [] })
    })

    render(<AdminRespondents />)
    expect(await screen.findByText(/0 results/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Search respondents'), { target: { value: 'VB10001' } })
    fireEvent.change(screen.getByLabelText('Filter by city'), { target: { value: 'Mumbai' } })
    fireEvent.click(screen.getByRole('button', { name: /csv/i }))

    await waitFor(() => expect(mocks.api.get).toHaveBeenCalledWith('/admin/members/export', {
      params: expect.objectContaining({ format: 'csv', search: 'VB10001', city: 'Mumbai' }),
      responseType: 'blob',
    }))
    anchorClick.mockRestore()
  })

  it('shows an import preview before allowing confirmation', async () => {
    const job = { id: 5, filename: 'messy.csv', total_rows: 4, imported_rows: 0, skipped_rows: 0, corrected_rows: 0, error_rows: 0, status: 'PREVIEW', created_at: '2026-11-19T00:00:00' }
    const preview = {
      job,
      summary: { total_rows: 4, valid_rows: 1, needs_review: 1, skipped_rows: 2, corrections: 3 },
      rows: [{ row_number: 2, original_data: { name: 'Good Person' }, normalized_data: {}, corrections: [], errors: [], action: 'IMPORT' }],
    }
    mocks.api.get.mockImplementation((url) => {
      if (url === '/admin/imports') return Promise.resolve({ data: [job] })
      if (url === '/admin/imports/5/preview') return Promise.resolve({ data: preview })
      return Promise.resolve({ data: [] })
    })
    mocks.api.post.mockImplementation((url) => {
      if (url === '/admin/imports/upload') return Promise.resolve({ data: job })
      if (url === '/admin/imports/5/confirm') return Promise.resolve({ data: { ...job, status: 'CONFIRMED' } })
      return Promise.resolve({ data: {} })
    })

    render(<AdminImports />)
    const file = new File(['member_id,name\nVB1,Test\n'], 'messy.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByLabelText(/choose csv file/i), { target: { files: [file] } })

    expect(await screen.findByText(/Preview — messy.csv/)).toBeInTheDocument()
    expect(screen.getByText(/Skipped 2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /confirm import/i }))
    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledWith('/admin/imports/5/confirm'))
  })
})

describe('questionnaire runtime', () => {
  it('starts a questionnaire and autosaves an answer', async () => {
    mocks.api.get.mockRejectedValue({ response: { status: 404 } })
    const step = {
      response_id: 3, status: 'IN_PROGRESS', version: 1, progress: 0, termination_reason: null,
      question: { id: 'Q1', type: 'single', text: 'Mode?', options: ['Car', 'Bike'], min: null, max: null, required: true },
    }
    mocks.api.post.mockImplementation((url) => {
      if (url.endsWith('/start')) return Promise.resolve({ data: step })
      if (url.endsWith('/answer')) return Promise.resolve({ data: { ...step, progress: 50, question: { ...step.question, id: 'Q2', text: 'Why Car?' } } })
      return Promise.resolve({ data: {} })
    })

    render(<MemoryRouter initialEntries={['/member/surveys/11/respond']}>
      <Routes><Route path="/member/surveys/:surveyId/respond" element={<MemberQuestionnaire />} /></Routes>
    </MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: /start questionnaire/i }))
    expect(await screen.findByText('Mode?')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Car'))
    fireEvent.click(screen.getByRole('button', { name: /save & next/i }))
    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledWith(
      '/members/me/surveys/11/response/answer', { question_id: 'Q1', value: 'Car' },
    ))
    expect(await screen.findByText('Why Car?')).toBeInTheDocument()
  })

  it('shows line-numbered validation errors and version history', async () => {
    mocks.api.get.mockImplementation((url) => {
      if (url === '/admin/surveys') return Promise.resolve({ data: [{ id: 11, title: 'Mobility survey' }] })
      if (url.endsWith('/versions')) return Promise.resolve({ data: [
        { id: 1, survey_id: 11, version: 1, status: 'ACTIVE', question_count: 2, created_at: '2026-11-24T00:00:00' },
      ] })
      if (url.endsWith('/analytics')) return Promise.resolve({ data: {
        survey_id: 11, active_version: 1, started: 2, completed: 1, in_progress: 1, terminated: 0,
        questions: [{ id: 'Q1', text: 'Mode?', reached: 2, answered: 1, dropoff: 1 }],
        termination_reasons: [], quality_flags: { speeders: 0, minimum_completes_for_speeder_check: 5 },
      } })
      return Promise.resolve({ data: [] })
    })
    mocks.api.post.mockImplementation((url) => url.endsWith('/validate')
      ? Promise.resolve({ data: { valid: false, errors: [{ line: 2, code: 'UNKNOWN_DIRECTIVE', message: 'Bad line' }] } })
      : Promise.resolve({ data: {} }))

    render(<MemoryRouter initialEntries={['/admin/surveys/11/questionnaire']}>
      <Routes><Route path="/admin/surveys/:surveyId/questionnaire" element={<AdminQuestionnaire />} /></Routes>
    </MemoryRouter>)
    expect(await screen.findByText('v1')).toBeInTheDocument()
    expect(screen.getByText('Drop-off by question')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/Line 2: Bad line/)
    expect(screen.getByRole('button', { name: 'Line 2' })).toBeInTheDocument()
  })
})

describe('route protection', () => {
  it('redirects a member away from admin pages', async () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={<ProtectedRoute allow={['ADMIN', 'OPERATIONS']}><div>Admin area</div></ProtectedRoute>} />
          <Route path="/member" element={<div>Member area</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText('Member area')).toBeInTheDocument()
    expect(screen.queryByText('Admin area')).not.toBeInTheDocument()
  })
})

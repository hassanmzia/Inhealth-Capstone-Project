import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { ArrowLeft, UserPlus, Save } from 'lucide-react'
import api from '@/services/api'

const DRAFT_KEY = 'newPatientDraft'

interface PatientFormData {
  first_name: string
  last_name: string
  middle_name?: string
  mrn: string
  birth_date: string
  gender: 'male' | 'female' | 'other' | 'unknown'
  email?: string
  phone?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string
}

function loadDraft(): Partial<PatientFormData> {
  try {
    return JSON.parse(sessionStorage.getItem(DRAFT_KEY) || '{}')
  } catch {
    return {}
  }
}

/** True only if the draft has user-entered data beyond bare defaults. */
function hasMeaningfulDraft(): boolean {
  const draft = loadDraft()
  const meaningful = ['first_name', 'last_name', 'mrn', 'birth_date', 'email', 'phone'] as const
  return meaningful.some((k) => !!draft[k])
}

export default function NewPatientPage() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)
  const submittedRef = useRef(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PatientFormData>({
    defaultValues: { gender: 'unknown', country: 'US', ...loadDraft() },
  })

  // Persist form data to sessionStorage on every change so a page reload
  // (Vite HMR, nginx restart, etc.) doesn't lose the user's work.
  const watchedValues = watch()
  useEffect(() => {
    if (!submittedRef.current) {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(watchedValues))
    }
  }, [watchedValues])

  const createMutation = useMutation({
    mutationFn: (data: PatientFormData) => api.post('/patients/', data).then((r) => r.data),
    onSuccess: (patient) => {
      submittedRef.current = true
      sessionStorage.removeItem(DRAFT_KEY)
      navigate(`/patients/${patient.id}`)
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        JSON.stringify(err?.response?.data) ||
        'Failed to create patient'
      setServerError(msg)
    },
  })

  const onSubmit = (data: PatientFormData) => {
    setServerError(null)
    createMutation.mutate(data)
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/patients')}
          className="p-2 rounded-lg border border-border hover:bg-accent text-muted-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-primary-500" />
            Add New Patient
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Register a new patient in the system
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {serverError && (
          <div className="p-4 rounded-lg bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 text-danger-700 dark:text-danger-400 text-sm">
            {serverError}
          </div>
        )}

        {/* Draft restored banner */}
        {hasMeaningfulDraft() && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 text-warning-700 dark:text-warning-400 text-sm">
            <span>Draft restored after page reload.</span>
            <button
              type="button"
              onClick={() => { sessionStorage.removeItem(DRAFT_KEY); window.location.reload() }}
              className="underline text-xs ml-4 hover:opacity-75"
            >
              Clear draft
            </button>
          </div>
        )}

        {/* Identity */}
        <section className="clinical-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-foreground border-b border-border pb-2">
            Patient Identity
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                First Name <span className="text-danger-500">*</span>
              </label>
              <input
                {...register('first_name', { required: 'Required' })}
                className="input-field w-full"
                placeholder="John"
              />
              {errors.first_name && (
                <p className="text-xs text-danger-500 mt-1">{errors.first_name.message}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Middle Name</label>
              <input {...register('middle_name')} className="input-field w-full" placeholder="M." />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Last Name <span className="text-danger-500">*</span>
              </label>
              <input
                {...register('last_name', { required: 'Required' })}
                className="input-field w-full"
                placeholder="Doe"
              />
              {errors.last_name && (
                <p className="text-xs text-danger-500 mt-1">{errors.last_name.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Date of Birth <span className="text-danger-500">*</span>
              </label>
              <input
                type="date"
                {...register('birth_date', { required: 'Required' })}
                className="input-field w-full"
              />
              {errors.birth_date && (
                <p className="text-xs text-danger-500 mt-1">{errors.birth_date.message}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Gender <span className="text-danger-500">*</span>
              </label>
              <select {...register('gender')} className="input-field w-full">
                <option value="unknown">Unknown</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                MRN <span className="text-danger-500">*</span>
              </label>
              <input
                {...register('mrn', { required: 'Required' })}
                className="input-field w-full font-mono"
                placeholder="MRN-001234"
              />
              {errors.mrn && (
                <p className="text-xs text-danger-500 mt-1">{errors.mrn.message}</p>
              )}
            </div>
          </div>
        </section>

        {/* Contact */}
        <section className="clinical-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-foreground border-b border-border pb-2">
            Contact Information
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Email</label>
              <input
                type="email"
                {...register('email')}
                className="input-field w-full"
                placeholder="patient@example.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Phone</label>
              <input
                type="tel"
                {...register('phone')}
                className="input-field w-full"
                placeholder="+1 555 000 0000"
              />
            </div>
          </div>
        </section>

        {/* Address */}
        <section className="clinical-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-foreground border-b border-border pb-2">
            Address
          </h2>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Address Line 1
              </label>
              <input
                {...register('address_line1')}
                className="input-field w-full"
                placeholder="123 Main St"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Address Line 2
              </label>
              <input
                {...register('address_line2')}
                className="input-field w-full"
                placeholder="Apt 4B"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-foreground mb-1">City</label>
              <input {...register('city')} className="input-field w-full" placeholder="Springfield" />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">State</label>
              <input {...register('state')} className="input-field w-full" placeholder="IL" />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">ZIP</label>
              <input
                {...register('postal_code')}
                className="input-field w-full"
                placeholder="62701"
              />
            </div>
          </div>
          <div className="w-32">
            <label className="block text-xs font-medium text-foreground mb-1">Country</label>
            <input
              {...register('country')}
              className="input-field w-full"
              placeholder="US"
              defaultValue="US"
            />
          </div>
        </section>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/patients')}
            className="px-4 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || createMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Save className="w-4 h-4" />
            {createMutation.isPending ? 'Saving…' : 'Save Patient'}
          </button>
        </div>
      </form>
    </div>
  )
}

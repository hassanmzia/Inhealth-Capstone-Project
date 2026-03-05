import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import {
  Heart,
  Eye,
  EyeOff,
  Loader2,
  Shield,
  Activity,
  BrainCircuit,
  Lock,
  Mail,
  User,
  Phone,
  Sun,
  Moon,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const registerSchema = z
  .object({
    email: z.string().email('Enter a valid email address'),
    first_name: z.string().min(1, 'First name is required'),
    last_name: z.string().min(1, 'Last name is required'),
    phone_number: z.string().optional(),
    password: z.string().min(12, 'Password must be at least 12 characters'),
    password_confirm: z.string().min(12, 'Please confirm your password'),
    role: z.enum(['patient', 'physician', 'nurse', 'researcher']).default('patient'),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  })

type RegisterForm = z.infer<typeof registerSchema>

const FEATURES = [
  { icon: BrainCircuit, title: '25 AI Agents', desc: 'Autonomous clinical intelligence agents working 24/7' },
  { icon: Activity, title: 'Real-Time Monitoring', desc: 'Live vitals, CGM, and IoT device integration' },
  { icon: Shield, title: 'HIPAA Compliant', desc: 'Enterprise-grade security and audit trails' },
]

const ROLES = [
  { value: 'patient', label: 'Patient' },
  { value: 'physician', label: 'Physician' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'researcher', label: 'Researcher' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser, isLoading } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.classList.contains('dark'),
  )

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'patient' },
  })

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser(data)
      toast.success('Account created! Please check your email to verify your account.')
      navigate('/login')
    } catch (error: unknown) {
      const err = error as { response?: { data?: Record<string, string[]> }; userMessage?: string }
      const detail = err?.response?.data
      if (detail) {
        const first = Object.values(detail)[0]
        toast.error(Array.isArray(first) ? first[0] : String(first))
      } else {
        toast.error(err?.userMessage ?? 'Registration failed. Please try again.')
      }
    }
  }

  const toggleTheme = () => {
    setIsDark((v) => {
      const next = !v
      document.documentElement.classList.toggle('dark', next)
      return next
    })
  }

  return (
    <div className={cn('min-h-screen flex', isDark && 'dark')}>
      {/* Left: Hero */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-2/5 bg-gradient-clinical flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute -bottom-40 -left-20 w-80 h-80 rounded-full bg-white/5 blur-3xl" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Heart className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-xl leading-none">InHealth</p>
              <p className="text-blue-200 text-sm leading-none">Chronic Care Platform</p>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-16"
          >
            <h1 className="text-4xl font-bold text-white leading-tight">
              Join the Future<br />
              <span className="text-blue-200">of Chronic Care</span>
            </h1>
            <p className="text-blue-100 text-lg mt-4 max-w-md leading-relaxed">
              Create your account and connect with 25 intelligent agents delivering
              precision care around the clock.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-12 space-y-4"
          >
            {FEATURES.map((f) => (
              <div key={f.title} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center flex-shrink-0">
                  <f.icon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{f.title}</p>
                  <p className="text-blue-200 text-xs mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-4 text-blue-200 text-xs">
            <span>HIPAA Compliant</span>
            <span>·</span>
            <span>SOC 2 Type II</span>
            <span>·</span>
            <span>HL7 FHIR R4</span>
          </div>
        </div>
      </div>

      {/* Right: Registration form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 bg-background overflow-y-auto">
        <button
          onClick={toggleTheme}
          className="absolute top-6 right-6 p-2 rounded-lg bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <div className="lg:hidden flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-gradient-clinical flex items-center justify-center">
            <Heart className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg text-foreground">InHealth Chronic Care</span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-foreground">Create your account</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-primary-600 dark:text-primary-400 hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Name row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">First name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    {...register('first_name')}
                    type="text"
                    autoComplete="given-name"
                    placeholder="Jane"
                    className={cn(
                      'w-full pl-10 pr-3 py-2.5 rounded-lg border bg-card text-foreground text-sm',
                      'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
                      'placeholder:text-muted-foreground',
                      errors.first_name ? 'border-danger-400' : 'border-border',
                    )}
                  />
                </div>
                {errors.first_name && (
                  <p className="mt-1 text-xs text-danger-500">{errors.first_name.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Last name</label>
                <input
                  {...register('last_name')}
                  type="text"
                  autoComplete="family-name"
                  placeholder="Smith"
                  className={cn(
                    'w-full px-3 py-2.5 rounded-lg border bg-card text-foreground text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
                    'placeholder:text-muted-foreground',
                    errors.last_name ? 'border-danger-400' : 'border-border',
                  )}
                />
                {errors.last_name && (
                  <p className="mt-1 text-xs text-danger-500">{errors.last_name.message}</p>
                )}
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Email address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  placeholder="physician@hospital.com"
                  className={cn(
                    'w-full pl-10 pr-4 py-2.5 rounded-lg border bg-card text-foreground text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
                    'placeholder:text-muted-foreground',
                    errors.email ? 'border-danger-400' : 'border-border',
                  )}
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-xs text-danger-500">{errors.email.message}</p>
              )}
            </div>

            {/* Phone (optional) */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Phone number <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  {...register('phone_number')}
                  type="tel"
                  autoComplete="tel"
                  placeholder="+1 (555) 000-0000"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent placeholder:text-muted-foreground"
                />
              </div>
            </div>

            {/* Role */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Role</label>
              <select
                {...register('role')}
                className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Min. 12 characters"
                  className={cn(
                    'w-full pl-10 pr-10 py-2.5 rounded-lg border bg-card text-foreground text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
                    'placeholder:text-muted-foreground',
                    errors.password ? 'border-danger-400' : 'border-border',
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-danger-500">{errors.password.message}</p>
              )}
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Confirm password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  {...register('password_confirm')}
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Re-enter password"
                  className={cn(
                    'w-full pl-10 pr-10 py-2.5 rounded-lg border bg-card text-foreground text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
                    'placeholder:text-muted-foreground',
                    errors.password_confirm ? 'border-danger-400' : 'border-border',
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password_confirm && (
                <p className="mt-1 text-xs text-danger-500">{errors.password_confirm.message}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-clinical text-white rounded-lg font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4" />
                  Create Account
                </>
              )}
            </button>
          </form>

          <p className="text-center text-xs text-muted-foreground mt-6">
            By creating an account, you agree to our{' '}
            <a href="#" className="text-primary-600 hover:underline">Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="text-primary-600 hover:underline">Privacy Policy</a>
          </p>
        </motion.div>
      </div>
    </div>
  )
}

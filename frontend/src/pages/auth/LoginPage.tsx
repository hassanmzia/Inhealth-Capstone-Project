import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
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
  KeyRound,
  Sun,
  Moon,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  totpCode: z.string().optional(),
})

type LoginForm = z.infer<typeof loginSchema>

const FEATURES = [
  { icon: BrainCircuit, title: '25 AI Agents', desc: 'Autonomous clinical intelligence agents working 24/7' },
  { icon: Activity, title: 'Real-Time Monitoring', desc: 'Live vitals, CGM, and IoT device integration' },
  { icon: Shield, title: 'HIPAA Compliant', desc: 'Enterprise-grade security and audit trails' },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isLoading, requires2FA } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.classList.contains('dark'),
  )

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/dashboard'

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    try {
      const result = await login(data)
      if (!result.requires2FA) {
        toast.success(`Welcome back, ${result.user.firstName}!`)
        navigate(from, { replace: true })
      }
    } catch (error: unknown) {
      const message = (error as { userMessage?: string })?.userMessage ?? 'Login failed. Please try again.'
      toast.error(message)
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
      <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 bg-gradient-clinical flex-col justify-between p-12 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute -bottom-40 -left-20 w-80 h-80 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute top-1/3 left-1/4 w-64 h-64 rounded-full bg-blue-400/10 blur-2xl" />
        </div>

        {/* Content */}
        <div className="relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Heart className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-xl leading-none">InHealth</p>
              <p className="text-blue-200 text-sm leading-none">Chronic Care Platform</p>
            </div>
          </div>

          {/* Hero text */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-16"
          >
            <h1 className="text-4xl xl:text-5xl font-bold text-white leading-tight">
              AI-Powered<br />
              <span className="text-blue-200">Chronic Disease</span><br />
              Management
            </h1>
            <p className="text-blue-100 text-lg mt-4 max-w-md leading-relaxed">
              25 intelligent agents working in harmony to deliver precision care,
              prevent complications, and improve patient outcomes at scale.
            </p>
          </motion.div>

          {/* Features */}
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

        {/* Bottom */}
        <div className="relative z-10">
          <div className="flex items-center gap-4 text-blue-200 text-xs">
            <span>HIPAA Compliant</span>
            <span>·</span>
            <span>SOC 2 Type II</span>
            <span>·</span>
            <span>HL7 FHIR R4</span>
            <span>·</span>
            <span>ONC Certified</span>
          </div>
        </div>

        {/* Animated vitals wave */}
        <div className="absolute bottom-24 right-8 w-48 h-20 opacity-30">
          <svg viewBox="0 0 200 80" className="w-full h-full">
            <polyline
              points="0,40 20,40 30,10 40,70 50,20 60,60 70,40 90,40 100,5 110,75 120,30 130,50 140,40 160,40 170,15 180,65 190,40 200,40"
              fill="none"
              stroke="white"
              strokeWidth="2"
              className="animate-pulse"
            />
          </svg>
        </div>
      </div>

      {/* Right: Login form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 bg-background">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="absolute top-6 right-6 p-2 rounded-lg bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Mobile logo */}
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
          {/* Heading */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">Sign in to your account</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              Enter your credentials to access the platform, or{' '}
              <Link to="/register" className="text-primary-600 dark:text-primary-400 hover:underline font-medium">
                create an account
              </Link>
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Email address
              </label>
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

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-foreground">Password</label>
                <button
                  type="button"
                  className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
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

            {/* 2FA code (conditional) */}
            {requires2FA && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
              >
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Two-Factor Authentication Code
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    {...register('totpCode')}
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="000000"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-card text-foreground text-sm font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary-400 placeholder:text-muted-foreground"
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Enter the 6-digit code from your authenticator app
                </p>
              </motion.div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-clinical text-white rounded-lg font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed mt-6"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4" />
                  Sign In Securely
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs text-muted-foreground">Or continue with</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* OAuth buttons */}
          <div className="grid grid-cols-2 gap-3">
            {['Microsoft', 'Google'].map((provider) => (
              <button
                key={provider}
                type="button"
                className="flex items-center justify-center gap-2 px-4 py-2.5 border border-border rounded-lg text-sm font-medium text-foreground bg-card hover:bg-accent transition-colors"
              >
                {provider}
              </button>
            ))}
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-muted-foreground mt-8">
            By signing in, you agree to our{' '}
            <a href="#" className="text-primary-600 hover:underline">Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="text-primary-600 hover:underline">Privacy Policy</a>
          </p>
        </motion.div>
      </div>
    </div>
  )
}

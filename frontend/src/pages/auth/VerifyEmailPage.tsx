import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle, XCircle, Loader2, Heart } from 'lucide-react'
import api from '@/services/api'

type VerifyState = 'loading' | 'success' | 'error' | 'missing'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [state, setState] = useState<VerifyState>(token ? 'loading' : 'missing')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) return

    api
      .post('/auth/verify-email/', { token })
      .then((res) => {
        setMessage(res.data.message ?? 'Email verified successfully.')
        setState('success')
        // Redirect to login after 3s
        setTimeout(() => navigate('/login', { replace: true }), 3000)
      })
      .catch((err) => {
        setMessage(
          err?.response?.data?.error ?? 'Invalid or expired verification link.',
        )
        setState('error')
      })
  }, [token, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-blue-50 dark:from-gray-950 dark:to-gray-900 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 max-w-md w-full text-center space-y-6"
      >
        {/* Logo */}
        <div className="flex justify-center">
          <div className="w-12 h-12 bg-primary-500 rounded-xl flex items-center justify-center">
            <Heart className="w-7 h-7 text-white" />
          </div>
        </div>

        {state === 'loading' && (
          <>
            <Loader2 className="w-12 h-12 mx-auto text-primary-500 animate-spin" />
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Verifying your email…
            </h1>
          </>
        )}

        {state === 'success' && (
          <>
            <CheckCircle className="w-12 h-12 mx-auto text-green-500" />
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Email Verified!
            </h1>
            <p className="text-gray-600 dark:text-gray-400">{message}</p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              Redirecting to login…
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Go to Login
            </Link>
          </>
        )}

        {(state === 'error' || state === 'missing') && (
          <>
            <XCircle className="w-12 h-12 mx-auto text-red-500" />
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Verification Failed
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {state === 'missing'
                ? 'No verification token found. Please use the link from your email.'
                : message}
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Back to Login
            </Link>
          </>
        )}
      </motion.div>
    </div>
  )
}

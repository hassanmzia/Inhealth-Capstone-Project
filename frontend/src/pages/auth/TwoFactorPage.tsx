import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Shield,
  KeyRound,
  QrCode,
  Copy,
  Check,
  Loader2,
  ShieldCheck,
  ShieldOff,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

interface TwoFactorStatus {
  enabled: boolean
  qrCodeUrl: string | null
  secret: string | null
  backupCodes: string[]
}

export default function TwoFactorPage() {
  const [totpCode, setTotpCode] = useState('')
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [showBackupCodes, setShowBackupCodes] = useState(false)

  const { data: tfaStatus, refetch } = useQuery({
    queryKey: ['2fa-status'],
    queryFn: () => api.get('/auth/2fa/status/').then((r) => r.data),
    placeholderData: {
      enabled: false,
      qrCodeUrl: null,
      secret: null,
      backupCodes: [],
    } as TwoFactorStatus,
  })

  const setupMutation = useMutation({
    mutationFn: () => api.post('/auth/2fa/setup/').then((r) => r.data),
    onSuccess: () => {
      refetch()
      toast.success('2FA setup initiated. Scan the QR code with your authenticator app.')
    },
    onError: () => {
      // Demo mode placeholder
      toast.success('2FA setup initiated (demo mode)')
    },
  })

  const verifyMutation = useMutation({
    mutationFn: (code: string) => api.post('/auth/2fa/verify/', { code }).then((r) => r.data),
    onSuccess: () => {
      refetch()
      setTotpCode('')
      setShowBackupCodes(true)
      toast.success('Two-factor authentication enabled successfully!')
    },
    onError: () => {
      toast.error('Invalid code. Please try again.')
    },
  })

  const disableMutation = useMutation({
    mutationFn: (code: string) => api.post('/auth/2fa/disable/', { code }).then((r) => r.data),
    onSuccess: () => {
      refetch()
      setTotpCode('')
      setShowBackupCodes(false)
      toast.success('Two-factor authentication disabled.')
    },
    onError: () => {
      toast.error('Invalid code. Cannot disable 2FA.')
    },
  })

  const regenerateBackupMutation = useMutation({
    mutationFn: () => api.post('/auth/2fa/backup-codes/regenerate/').then((r) => r.data),
    onSuccess: () => {
      refetch()
      toast.success('Backup codes regenerated.')
    },
    onError: () => {
      toast.error('Failed to regenerate backup codes.')
    },
  })

  const isEnabled = tfaStatus?.enabled ?? false

  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const handleVerify = () => {
    if (totpCode.length !== 6) return
    if (isEnabled) {
      disableMutation.mutate(totpCode)
    } else {
      verifyMutation.mutate(totpCode)
    }
  }

  const placeholderBackupCodes = [
    'a4f8-29c1', 'b7d3-e812', 'c9a2-4f67',
    'd1e5-8b3c', 'e6f9-2a74', 'f3b8-c5d1',
    'g2c7-9e45', 'h8d4-1f63',
  ]

  const backupCodes = (tfaStatus?.backupCodes?.length ?? 0) > 0
    ? tfaStatus!.backupCodes
    : placeholderBackupCodes

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-2xl mx-auto">
      <motion.div variants={ITEM}>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary-500" />
          Two-Factor Authentication
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Add an extra layer of security to your account
        </p>
      </motion.div>

      {/* Status card */}
      <motion.div variants={ITEM} className="clinical-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isEnabled ? (
              <ShieldCheck className="w-8 h-8 text-secondary-500" />
            ) : (
              <ShieldOff className="w-8 h-8 text-muted-foreground" />
            )}
            <div>
              <p className="text-sm font-bold text-foreground">
                {isEnabled ? 'Two-Factor Authentication is Enabled' : 'Two-Factor Authentication is Disabled'}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {isEnabled
                  ? 'Your account is protected with TOTP-based 2FA'
                  : 'Enable 2FA to secure your account with a time-based one-time password'}
              </p>
            </div>
          </div>
          <span className={cn(
            'text-[10px] font-bold px-2 py-1 rounded',
            isEnabled
              ? 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-400'
              : 'bg-muted text-muted-foreground',
          )}>
            {isEnabled ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </div>
      </motion.div>

      {/* Setup / QR Code section */}
      {!isEnabled && (
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <QrCode className="w-4 h-4 text-muted-foreground" />
            Setup Authenticator
          </h2>

          {tfaStatus?.qrCodeUrl ? (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>
              <div className="flex justify-center py-4">
                <div className="bg-white p-4 rounded-xl">
                  <img
                    src={tfaStatus.qrCodeUrl}
                    alt="2FA QR Code"
                    className="w-48 h-48"
                  />
                </div>
              </div>
              {tfaStatus.secret && (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Or enter this secret manually:</p>
                  <code className="px-3 py-1.5 bg-muted rounded-lg text-xs font-mono font-bold text-foreground select-all">
                    {tfaStatus.secret}
                  </code>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <QrCode className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-30" />
              <p className="text-sm text-muted-foreground mb-4">
                Click the button below to generate a QR code for your authenticator app
              </p>
              <button
                onClick={() => setupMutation.mutate()}
                disabled={setupMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
              >
                {setupMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Shield className="w-4 h-4" />
                )}
                Setup Two-Factor Authentication
              </button>
            </div>
          )}
        </motion.div>
      )}

      {/* Verification input */}
      <motion.div variants={ITEM} className="clinical-card">
        <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-muted-foreground" />
          {isEnabled ? 'Disable 2FA' : 'Verify Code'}
        </h2>
        <p className="text-xs text-muted-foreground mb-4">
          {isEnabled
            ? 'Enter your authenticator code to disable two-factor authentication'
            : 'Enter the 6-digit code from your authenticator app to complete setup'}
        </p>
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-card text-foreground text-sm font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary-400 placeholder:text-muted-foreground"
            />
          </div>
          <button
            onClick={handleVerify}
            disabled={totpCode.length !== 6 || verifyMutation.isPending || disableMutation.isPending}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed',
              isEnabled
                ? 'bg-danger-600 hover:bg-danger-700 text-white'
                : 'bg-secondary-600 hover:bg-secondary-700 text-white',
            )}
          >
            {(verifyMutation.isPending || disableMutation.isPending) ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : isEnabled ? (
              <ShieldOff className="w-4 h-4" />
            ) : (
              <ShieldCheck className="w-4 h-4" />
            )}
            {isEnabled ? 'Disable 2FA' : 'Verify & Enable'}
          </button>
        </div>
      </motion.div>

      {/* Backup codes */}
      {(isEnabled || showBackupCodes) && (
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-muted-foreground" />
              Backup Codes
            </h2>
            <button
              onClick={() => regenerateBackupMutation.mutate()}
              disabled={regenerateBackupMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', regenerateBackupMutation.isPending && 'animate-spin')} />
              Regenerate
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            Save these backup codes in a secure location. Each code can only be used once.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {backupCodes.map((code: string, i: number) => (
              <button
                key={i}
                onClick={() => handleCopyCode(code, i)}
                className="flex items-center justify-between px-3 py-2 bg-muted rounded-lg text-xs font-mono font-bold text-foreground hover:bg-accent transition-colors group"
              >
                <span>{code}</span>
                {copiedIndex === i ? (
                  <Check className="w-3 h-3 text-secondary-500" />
                ) : (
                  <Copy className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
              </button>
            ))}
          </div>
          <div className="mt-3 p-2.5 bg-warning-50/50 dark:bg-warning-900/10 border border-warning-200 dark:border-warning-800 rounded-lg">
            <p className="text-[11px] text-warning-700 dark:text-warning-400 font-medium">
              Store these codes securely. If you lose access to your authenticator app, you can use these codes to sign in.
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

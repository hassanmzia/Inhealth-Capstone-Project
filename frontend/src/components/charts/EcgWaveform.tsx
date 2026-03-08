import { useEffect, useRef, useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import type { EcgRhythm, VitalStatus } from '@/types/clinical'
import { ECG_RHYTHM_LABELS, ECG_RHYTHM_STATUS } from '@/types/clinical'

interface EcgWaveformProps {
  heartRate?: number
  rhythm?: EcgRhythm
  /** Pre-generated waveform samples (overrides internal generation) */
  waveformData?: number[]
  width?: number
  height?: number
  /** Seconds of ECG trace visible */
  duration?: number
  /** Color of the trace line */
  color?: string
  /** Whether the waveform is actively animating */
  isLive?: boolean
  /** Show the rhythm label and heart rate overlay */
  showOverlay?: boolean
  /** Compact mode for small displays */
  compact?: boolean
}

// ─── PQRST Wave Generator ────────────────────────────────────────────────────

const SAMPLE_RATE = 250 // samples per second

/**
 * Generate a single PQRST heartbeat waveform.
 * Returns an array of amplitude values for one complete cardiac cycle.
 */
function generatePQRST(samplesPerBeat: number, rhythm: EcgRhythm): number[] {
  const samples = new Array(samplesPerBeat).fill(0)

  // Normalize time 0..1 for each beat
  for (let i = 0; i < samplesPerBeat; i++) {
    const t = i / samplesPerBeat

    switch (rhythm) {
      case 'atrial_fibrillation':
        samples[i] = generateAfibBeat(t)
        break
      case 'atrial_flutter':
        samples[i] = generateFlutterBeat(t)
        break
      case 'ventricular_tachycardia':
        samples[i] = generateVtachBeat(t)
        break
      case 'ventricular_fibrillation':
        samples[i] = generateVfibSample(t)
        break
      default:
        // Normal sinus, bradycardia, tachycardia — same morphology, different rate
        samples[i] = generateNormalBeat(t)
        break
    }
  }

  return samples
}

/** Standard PQRST complex */
function generateNormalBeat(t: number): number {
  let v = 0

  // P wave: small upward deflection at ~0.10-0.18
  v += 0.12 * gaussian(t, 0.14, 0.02)

  // Q wave: small downward deflection at ~0.22
  v -= 0.08 * gaussian(t, 0.22, 0.008)

  // R wave: tall sharp peak at ~0.25
  v += 1.0 * gaussian(t, 0.25, 0.012)

  // S wave: downward deflection at ~0.28
  v -= 0.18 * gaussian(t, 0.28, 0.01)

  // T wave: broad upward deflection at ~0.40
  v += 0.25 * gaussian(t, 0.42, 0.035)

  // Baseline noise
  v += 0.01 * Math.sin(t * Math.PI * 60)

  return v
}

/** Atrial fibrillation: no P wave, irregular baseline, normal QRS */
function generateAfibBeat(t: number): number {
  let v = 0

  // Fibrillatory baseline (irregular, no P wave)
  v += 0.06 * Math.sin(t * Math.PI * 28 + Math.random() * 0.5)
  v += 0.04 * Math.sin(t * Math.PI * 42 + Math.random() * 0.3)

  // QRS complex
  v -= 0.08 * gaussian(t, 0.22, 0.008)
  v += 1.0 * gaussian(t, 0.25, 0.012)
  v -= 0.18 * gaussian(t, 0.28, 0.01)

  // T wave (slightly abnormal)
  v += 0.2 * gaussian(t, 0.42, 0.04)

  return v
}

/** Atrial flutter: sawtooth F waves */
function generateFlutterBeat(t: number): number {
  let v = 0

  // Flutter (sawtooth) waves
  const flutterFreq = 5.0
  v += 0.15 * ((t * flutterFreq) % 1.0 - 0.5)

  // QRS complex (narrow)
  v -= 0.08 * gaussian(t, 0.25, 0.008)
  v += 1.0 * gaussian(t, 0.28, 0.012)
  v -= 0.15 * gaussian(t, 0.31, 0.01)

  return v
}

/** Ventricular tachycardia: wide bizarre QRS, no P wave */
function generateVtachBeat(t: number): number {
  let v = 0

  // Wide QRS complex (sinusoidal-like)
  v += 0.9 * gaussian(t, 0.30, 0.06)
  v -= 0.5 * gaussian(t, 0.45, 0.05)
  v += 0.15 * gaussian(t, 0.55, 0.04)

  // Baseline wander
  v += 0.05 * Math.sin(t * Math.PI * 8)

  return v
}

/** Ventricular fibrillation: chaotic irregular waveform */
function generateVfibSample(t: number): number {
  return (
    0.4 * Math.sin(t * Math.PI * 18 + Math.random() * 2) +
    0.3 * Math.sin(t * Math.PI * 31 + Math.random() * 3) +
    0.2 * Math.sin(t * Math.PI * 47 + Math.random()) +
    0.1 * (Math.random() - 0.5)
  )
}

/** Gaussian bell curve */
function gaussian(x: number, mean: number, sigma: number): number {
  const d = (x - mean) / sigma
  return Math.exp(-0.5 * d * d)
}

/**
 * Generate continuous ECG waveform data for a given duration.
 */
function generateEcgSignal(
  heartRate: number,
  rhythm: EcgRhythm,
  durationSeconds: number,
): number[] {
  const totalSamples = Math.floor(SAMPLE_RATE * durationSeconds)
  const beatsPerSecond = heartRate / 60
  const samplesPerBeat = Math.floor(SAMPLE_RATE / beatsPerSecond)

  const signal: number[] = []

  while (signal.length < totalSamples) {
    // For afib, add beat-to-beat variability
    const effectiveSamplesPerBeat =
      rhythm === 'atrial_fibrillation'
        ? Math.floor(samplesPerBeat * (0.7 + Math.random() * 0.6))
        : samplesPerBeat

    const beat = generatePQRST(effectiveSamplesPerBeat, rhythm)
    signal.push(...beat)
  }

  return signal.slice(0, totalSamples)
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function EcgWaveform({
  heartRate = 72,
  rhythm = 'normal_sinus',
  waveformData,
  width = 600,
  height = 200,
  duration = 4,
  color,
  isLive = true,
  showOverlay = true,
  compact = false,
}: EcgWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)
  const offsetRef = useRef(0)
  const signalRef = useRef<number[]>([])

  const status: VitalStatus = ECG_RHYTHM_STATUS[rhythm] ?? 'normal'
  const traceColor =
    color ??
    (status === 'critical' ? '#e11d48' : status === 'warning' ? '#d97706' : '#22c55e')

  // Generate or use provided signal
  useEffect(() => {
    if (waveformData && waveformData.length > 0) {
      signalRef.current = waveformData
    } else if (heartRate > 0) {
      // Generate signal for both live (looping animation) and static (single-frame) display
      signalRef.current = generateEcgSignal(heartRate, rhythm, duration * 2)
    } else {
      // No heart rate data — show flatline
      signalRef.current = []
    }
    offsetRef.current = 0
  }, [heartRate, rhythm, duration, waveformData])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.width / dpr
    const h = canvas.height / dpr

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const signal = signalRef.current

    // When no signal data, draw a flatline (monitor off)
    if (signal.length === 0) {
      // Draw grid
      ctx.strokeStyle = 'rgba(128, 128, 128, 0.08)'
      ctx.lineWidth = 0.5 * dpr
      const gs = compact ? 15 : 20
      for (let x = 0; x < w; x += gs) { ctx.beginPath(); ctx.moveTo(x * dpr, 0); ctx.lineTo(x * dpr, canvas.height); ctx.stroke() }
      for (let y = 0; y < h; y += gs) { ctx.beginPath(); ctx.moveTo(0, y * dpr); ctx.lineTo(canvas.width, y * dpr); ctx.stroke() }

      // Flatline
      ctx.beginPath()
      ctx.strokeStyle = 'rgba(100, 100, 100, 0.4)'
      ctx.lineWidth = 1.5 * dpr
      ctx.moveTo(0, h * dpr / 2)
      ctx.lineTo(canvas.width, h * dpr / 2)
      ctx.stroke()
      return
    }

    if (signal.length === 0) return

    // Background grid (subtle)
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.08)'
    ctx.lineWidth = 0.5 * dpr
    const gridSize = compact ? 15 : 20
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath()
      ctx.moveTo(x * dpr, 0)
      ctx.lineTo(x * dpr, canvas.height)
      ctx.stroke()
    }
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath()
      ctx.moveTo(0, y * dpr)
      ctx.lineTo(canvas.width, y * dpr)
      ctx.stroke()
    }

    // Draw ECG trace
    const samplesVisible = Math.floor(SAMPLE_RATE * duration)
    const offset = Math.floor(offsetRef.current)

    ctx.beginPath()
    ctx.strokeStyle = traceColor
    ctx.lineWidth = (compact ? 1.5 : 2) * dpr
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'

    // Find signal min/max for scaling
    let minVal = Infinity
    let maxVal = -Infinity
    for (let i = 0; i < samplesVisible; i++) {
      const idx = (offset + i) % signal.length
      const val = signal[idx]
      if (val < minVal) minVal = val
      if (val > maxVal) maxVal = val
    }
    const range = maxVal - minVal || 1
    const padding = compact ? 0.15 : 0.1

    for (let i = 0; i < samplesVisible; i++) {
      const idx = (offset + i) % signal.length
      const val = signal[idx]

      const x = (i / samplesVisible) * w * dpr
      const y = (1.0 - padding - ((val - minVal) / range) * (1.0 - 2 * padding)) * h * dpr

      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.stroke()

    // Sweep line (green phosphor effect)
    if (isLive) {
      const sweepX = w * dpr
      const gradient = ctx.createLinearGradient(sweepX - 30 * dpr, 0, sweepX, 0)
      gradient.addColorStop(0, 'transparent')
      gradient.addColorStop(1, traceColor + '40')
      ctx.fillStyle = gradient
      ctx.fillRect(sweepX - 30 * dpr, 0, 30 * dpr, canvas.height)
    }

    // Advance offset for animation
    if (isLive) {
      offsetRef.current += SAMPLE_RATE / 60 // 60fps
      if (offsetRef.current >= signal.length) {
        offsetRef.current = 0
      }
      animationRef.current = requestAnimationFrame(draw)
    }
  }, [traceColor, duration, isLive, compact])

  // Canvas setup + animation loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`

    if (isLive) {
      animationRef.current = requestAnimationFrame(draw)
    } else {
      draw()
    }

    return () => {
      cancelAnimationFrame(animationRef.current)
    }
  }, [width, height, draw, isLive])

  return (
    <div className="relative" style={{ width, height }}>
      <canvas
        ref={canvasRef}
        className="rounded-lg bg-gray-950"
        style={{ width, height }}
      />

      {/* Overlay: rhythm label + heart rate */}
      {showOverlay && !isLive && signalRef.current.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-mono text-gray-600">
            No ECG data available
          </span>
        </div>
      )}
      {showOverlay && isLive && (
        <>
          {/* Top-left: Lead label */}
          <div className="absolute top-2 left-3 text-[10px] font-mono text-gray-500">
            Lead II
          </div>

          {/* Top-right: Heart rate */}
          <div className="absolute top-2 right-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span
              className={cn(
                'text-lg font-bold font-mono tabular-nums',
                status === 'critical'
                  ? 'text-red-400'
                  : status === 'warning'
                    ? 'text-yellow-400'
                    : 'text-green-400',
              )}
            >
              {heartRate}
            </span>
            <span className="text-[10px] text-gray-500">bpm</span>
          </div>

          {/* Bottom-left: Rhythm label */}
          <div
            className={cn(
              'absolute bottom-2 left-3 text-xs font-semibold px-2 py-0.5 rounded',
              status === 'critical'
                ? 'bg-red-900/60 text-red-300'
                : status === 'warning'
                  ? 'bg-yellow-900/60 text-yellow-300'
                  : 'bg-green-900/60 text-green-300',
            )}
          >
            {ECG_RHYTHM_LABELS[rhythm] ?? 'Unknown'}
          </div>

          {/* Bottom-right: Speed label */}
          {!compact && (
            <div className="absolute bottom-2 right-3 text-[10px] font-mono text-gray-600">
              25mm/s
            </div>
          )}
        </>
      )}
    </div>
  )
}

// Export the signal generator for use in the simulator
export { generateEcgSignal, SAMPLE_RATE }

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(n: number, decimals = 0): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals })
}

export function formatPercent(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`
}

export function formatCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()
}

export function truncate(s: string, length: number): string {
  if (s.length <= length) return s
  return `${s.slice(0, length)}...`
}

export function getRiskColor(category: string): string {
  switch (category) {
    case 'critical': return 'text-danger-600 dark:text-danger-400'
    case 'high': return 'text-orange-600 dark:text-orange-400'
    case 'medium': return 'text-warning-600 dark:text-warning-400'
    case 'low': return 'text-secondary-600 dark:text-secondary-400'
    default: return 'text-muted-foreground'
  }
}

export function getRiskBgColor(category: string): string {
  switch (category) {
    case 'critical': return 'bg-danger-100 dark:bg-danger-900/30'
    case 'high': return 'bg-orange-100 dark:bg-orange-900/30'
    case 'medium': return 'bg-warning-100 dark:bg-warning-900/30'
    case 'low': return 'bg-secondary-100 dark:bg-secondary-900/30'
    default: return 'bg-muted'
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-danger-600 dark:text-danger-400'
    case 'urgent': return 'text-warning-600 dark:text-warning-400'
    case 'soon': return 'text-primary-600 dark:text-primary-400'
    default: return 'text-muted-foreground'
  }
}

export function getVitalStatusColor(status: string): string {
  switch (status) {
    case 'critical': return 'text-danger-600 dark:text-danger-400'
    case 'warning': return 'text-warning-600 dark:text-warning-400'
    case 'normal': return 'text-secondary-600 dark:text-secondary-400'
    default: return 'text-muted-foreground'
  }
}

export function getAgentStatusColor(status: string): string {
  switch (status) {
    case 'running': return 'text-primary-600 dark:text-primary-400'
    case 'active': return 'text-secondary-600 dark:text-secondary-400'
    case 'error': return 'text-danger-600 dark:text-danger-400'
    case 'idle': return 'text-muted-foreground'
    case 'paused': return 'text-warning-600 dark:text-warning-400'
    default: return 'text-muted-foreground'
  }
}

export function getTierColor(tier: string): { bg: string; text: string; border: string } {
  switch (tier) {
    case 'tier1_ingestion':
      return { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' }
    case 'tier2_analysis':
      return { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' }
    case 'tier3_clinical':
      return { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-300', border: 'border-red-200 dark:border-red-800' }
    case 'tier4_coordination':
      return { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800' }
    case 'tier5_engagement':
      return { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-800' }
    default:
      return { bg: 'bg-muted', text: 'text-muted-foreground', border: 'border-border' }
  }
}

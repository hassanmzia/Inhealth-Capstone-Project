/**
 * InHealth PWA Service Worker
 *
 * Cache-first for static assets, network-first for API calls,
 * offline fallback for navigation requests.
 */

/// <reference lib="webworker" />

const CACHE_NAME = 'inhealth-v1'
const STATIC_ASSETS = ['/', '/index.html', '/manifest.json']

declare const self: ServiceWorkerGlobalScope

// Install — pre-cache shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  )
  self.skipWaiting()
})

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  )
  self.clients.claim()
})

// Fetch — strategy routing
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // API calls — network-first with cache fallback
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/agents/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful GET responses
          if (request.method === 'GET' && response.ok) {
            const clone = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          }
          return response
        })
        .catch(() => caches.match(request).then((cached) => cached || offlineResponse()))
    )
    return
  }

  // Static assets — cache-first
  if (
    url.pathname.match(/\.(js|css|png|jpg|jpeg|svg|gif|woff2?|ttf|eot|ico)$/)
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone()
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
            }
            return response
          })
      )
    )
    return
  }

  // Navigation — network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/index.html').then((cached) => cached || offlineResponse())
      )
    )
    return
  }

  // Default — network with cache fallback
  event.respondWith(fetch(request).catch(() => caches.match(request) as Promise<Response>))
})

function offlineResponse(): Response {
  return new Response(
    `<!DOCTYPE html>
<html><head><title>InHealth - Offline</title>
<style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0f172a;color:#e2e8f0}
.c{text-align:center;max-width:400px;padding:2rem}h1{color:#1d6fdb;font-size:1.5rem}p{opacity:.7;line-height:1.6}</style></head>
<body><div class="c"><h1>InHealth Offline</h1><p>You are currently offline. Please check your connection and try again.</p>
<button onclick="location.reload()" style="margin-top:1rem;padding:.5rem 1.5rem;background:#1d6fdb;color:#fff;border:none;border-radius:.375rem;cursor:pointer;font-size:.875rem">Retry</button></div></body></html>`,
    { headers: { 'Content-Type': 'text/html' }, status: 503 }
  )
}

export {}

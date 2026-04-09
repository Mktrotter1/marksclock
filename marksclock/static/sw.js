// Service worker for marksclock PWA
// Caches static assets for offline shell, but always fetches API live

const CACHE_NAME = 'marksclock-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/css/clock.css',
  '/static/js/app.js',
  '/static/js/utils.js',
  '/static/js/clock.js',
  '/static/js/timers.js',
  '/static/js/stopwatch.js',
  '/static/js/alarms.js',
  '/static/js/worldclock.js',
  '/static/js/pomodoro.js',
  '/static/js/calendar.js',
  '/static/js/converters.js',
  '/static/js/sun.js',
  '/static/js/reference.js',
  '/static/js/meeting.js',
  '/static/audio/alarm.wav',
  '/static/audio/timer.wav',
  '/static/audio/pomodoro.wav',
  '/static/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Always go to network for API and WebSocket
  if (url.pathname.startsWith('/api') || url.pathname === '/ws') {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      // Return cached, but also update cache in background
      const fetchPromise = fetch(event.request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
      return cached || fetchPromise;
    })
  );
});

// ExpenseAI Service Worker — PWA offline caching
const CACHE_NAME = 'expenseai-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/dashboard.js',
    '/static/js/chatbot.js',
    '/static/js/profile.js',
    'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
];

// Install — cache static shell
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch strategy: Network-first for API/HTML, Cache-first for static
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET and cross-origin API calls (currency rates, etc.)
    if (request.method !== 'GET') return;
    if (url.origin !== location.origin && !url.href.includes('fonts.googleapis') && !url.href.includes('cdn.jsdelivr')) return;

    // Static assets — cache first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then(cached => cached || fetch(request).then(resp => {
                const clone = resp.clone();
                caches.open(CACHE_NAME).then(c => c.put(request, clone));
                return resp;
            }))
        );
        return;
    }

    // HTML pages — network first with cache fallback
    event.respondWith(
        fetch(request)
            .then(resp => {
                if (resp.ok) {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(c => c.put(request, clone));
                }
                return resp;
            })
            .catch(() => caches.match(request))
    );
});

/* Quantum OTC Bot — service worker.
   PURPOSE: receive Web Push from the server and show a lock-screen notification on the
   phone EVEN WHEN THE APP IS CLOSED. Does NOT cache the dashboard or any /status data —
   the live UI must always come fresh from the network (no stale numbers, ever). */

self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(self.clients.claim()); });

// Push arrives from the server (a trade just went LIVE). Show it on the lock screen.
self.addEventListener('push', event => {
  let d = { title: '⚡ Quantum OTC Bot', body: 'Trade update', url: '/' };
  try { if (event.data) d = Object.assign(d, event.data.json()); } catch (e) {}
  const opts = {
    body: d.body,
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    tag: d.tag || 'otc-trade',
    renotify: true,
    vibrate: [200, 100, 200, 100, 300],
    data: { url: d.url || '/' },
    requireInteraction: false
  };
  event.waitUntil(self.registration.showNotification(d.title, opts));
});

// Tap the notification -> focus the app if open, else open it. The page then speaks the alert.
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) { if ('focus' in c) return c.focus(); }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

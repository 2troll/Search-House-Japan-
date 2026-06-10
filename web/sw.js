/* Service Worker — Casas Japón
 * Estrategia:
 *  - index.html (navegación): red primero, caché de respaldo (siempre fresco, pero
 *    funciona sin conexión).
 *  - data.geojson: caché primero + actualización en segundo plano (stale-while-
 *    revalidate). El mapa abre AL INSTANTE con los datos de la última visita y se
 *    refresca solo.
 *  - iconos/manifest: caché primero (no cambian casi nunca).
 *  - Tiles del mapa y fotos: red directa (cachearlos reventaría la cuota del móvil).
 */
const VER = 'cj-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest',
               'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== VER).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;           // tiles/fotos externas: red directa

  // Datos del mapa: instantáneo desde caché + refresco en segundo plano
  if (url.pathname.endsWith('data.geojson')) {
    e.respondWith(
      caches.open(VER).then(async c => {
        const cached = await c.match(e.request);
        const fresh = fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; })
                                      .catch(() => cached);
        return cached || fresh;
      })
    );
    return;
  }

  // Navegación (index.html): red primero, caché si no hay conexión
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(VER).then(c => c.put('index.html', copy));
        return r;
      }).catch(() => caches.match('index.html'))
    );
    return;
  }

  // Resto de estáticos propios (iconos, manifest): caché primero
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok && (url.pathname.includes('/icons/') || url.pathname.endsWith('.webmanifest'))) {
        const copy = r.clone();
        caches.open(VER).then(c => c.put(e.request, copy));
      }
      return r;
    }))
  );
});

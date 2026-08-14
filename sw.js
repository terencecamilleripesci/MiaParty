const C='mia-v20';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(['.','index.html','assets/mia.jpg','assets/bg.jpg','assets/icon-192.png','assets/icon-maskable-192.png'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))));self.clients.claim();});
/* Only ever touch our OWN small app files.
   Anything on the Pi (uploads, photos, the 18-minute video) must go straight to the
   network untouched: cloning a 96 MB streaming response to cache it broke video
   playback completely, and Cache.put() refuses 206 Partial Content outright — which is
   exactly what a <video> requests. Range requests are never intercepted. */
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (req.headers.has('range')) return;                    // video/audio seeking
  let url;
  try { url = new URL(req.url); } catch(_) { return; }
  if (url.origin !== self.location.origin) return;         // the Pi, fonts, anything remote
  if (/\.(mp4|mov|m4v|webm)$/i.test(url.pathname)) return;  // never cache media
  e.respondWith(
    fetch(req).then(r => {
      if (r && r.status === 200 && r.type === 'basic'){
        const cp = r.clone();
        caches.open(C).then(c => c.put(req, cp)).catch(()=>{});
      }
      return r;
    }).catch(() => caches.match(req))
  );
});

self.addEventListener('push',e=>{
  let d={title:"Mia's Party 🎀",body:'Something lovely is happening!',url:'./'};
  try{ d=Object.assign(d, e.data.json()); }catch(_){}
  e.waitUntil(self.registration.showNotification(d.title,{body:d.body,icon:'assets/icon-192.png',badge:'assets/icon-192.png',data:{url:d.url}}));
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data&&e.notification.data.url||'./'));
});

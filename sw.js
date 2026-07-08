const C='mia-v2';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(['.','index.html','assets/mia.jpg','assets/bg.jpg','assets/icon-192.png'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener('fetch',e=>{ if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));return r;}).catch(()=>caches.match(e.request)));});

self.addEventListener('push',e=>{
  let d={title:"Mia's Party 🎀",body:'Something lovely is happening!',url:'./'};
  try{ d=Object.assign(d, e.data.json()); }catch(_){}
  e.waitUntil(self.registration.showNotification(d.title,{body:d.body,icon:'assets/icon-192.png',badge:'assets/icon-192.png',data:{url:d.url}}));
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data&&e.notification.data.url||'./'));
});

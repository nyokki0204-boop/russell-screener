const SHELL='russell-shell-v1';
const FILES=['./','./index.html','./app.js','./style.css','./manifest.webmanifest','./icon-192.png','./icon-512.png','./icon.svg'];
self.addEventListener('install',event=>event.waitUntil(caches.open(SHELL).then(cache=>cache.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==SHELL).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET'||new URL(event.request.url).origin!==self.location.origin)return;
  if(new URL(event.request.url).pathname.includes('/data/'))return; // データの鮮度・整合性はアプリ側で管理
  event.respondWith(fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(SHELL).then(cache=>cache.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request)));
});

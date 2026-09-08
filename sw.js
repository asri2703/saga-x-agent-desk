/* ============================================================
   Saga X Agent Desk — service worker

   Served from the root, not /static/, because a service worker can
   only control the scope it is served from. At /static/js/sw.js it
   would control /static/ and nothing else, and push would never fire.

   Deliberately no offline caching. The desk shows live agent state;
   a cached copy of "everything is fine" from an hour ago is exactly
   the failure this project exists to remove.
   ============================================================ */

self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let d = { title: "Saga X Desk", body: "", url: "/", tag: "sagax" };
  try {
    if (event.data) d = Object.assign(d, event.data.json());
  } catch (err) {
    if (event.data) d.body = event.data.text();
  }
  event.waitUntil(
    self.registration.showNotification(d.title, {
      body: d.body,
      tag: d.tag,
      icon: "/static/icons/icon-192.png",
      badge: "/static/icons/icon-192.png",
      data: { url: d.url || "/" },
      // Infrastructure alerts should not vanish on their own.
      requireInteraction: true,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true })
      .then((list) => {
        // Focus the desk if it is already open rather than stacking tabs.
        for (const c of list) {
          if (c.url.includes(self.location.origin) && "focus" in c) {
            c.navigate(url);
            return c.focus();
          }
        }
        return self.clients.openWindow(url);
      })
  );
});

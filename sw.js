const CACHE_NAME = "copilote-bourse-pwa-v66";
const STATE_CACHE_NAME = "copilote-sw-state";
const USER_DATA_CACHE = "copilote-user-data-v1";
const STATE_CACHE_REQ = "./__copilote_sw_state__";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png"
];

function readSwState() {
  return caches.open(STATE_CACHE_NAME).then(function(cache) {
    return cache.match(STATE_CACHE_REQ).then(function(resp) {
      if (!resp) return { enabled: false, notifiedIds: [] };
      return resp.json().catch(function() { return { enabled: false, notifiedIds: [] }; });
    });
  }).catch(function() {
    return { enabled: false, notifiedIds: [] };
  });
}

function writeSwState(st) {
  return caches.open(STATE_CACHE_NAME).then(function(cache) {
    return cache.put(
      STATE_CACHE_REQ,
      new Response(JSON.stringify(st), { headers: { "Content-Type": "application/json" } })
    );
  }).catch(function() {});
}

function checkNewsInBackground() {
  return readSwState().then(function(st) {
    if (!st || !st.enabled) return;
    var ts = Date.now();
    return fetch("https://raw.githubusercontent.com/kira08200/Copilot-H24/main/news.json?t=" + ts, { cache: "no-store" })
      .then(function(r) { return r.ok ? r.json() : Promise.reject(); })
      .catch(function() {
        return fetch("./news.json?t=" + ts, { cache: "no-store" }).then(function(r) { return r.ok ? r.json() : null; });
      })
      .then(function(data) {
        if (!data) return;
        var seenMap = {};
        var list = Array.isArray(st.notifiedIds) ? st.notifiedIds.slice() : [];
        for (var s = 0; s < list.length; s++) seenMap[list[s]] = true;
        var hadSeed = list.length > 0;
        var pending = [];

        var moves = Array.isArray(data.majorMoves) ? data.majorMoves : [];
        for (var m = 0; m < moves.length; m++) {
          var mv = moves[m];
          if (!mv || !mv.id) continue;
          var mid = "mv_" + mv.id;
          if (!seenMap[mid]) {
            seenMap[mid] = true;
            list.push(mid);
            var sign = (mv.changePct || 0) >= 0 ? "+" : "";
            pending.push({
              title: (mv.kind === "drop" ? "📉 Chute : " : "🚀 Hausse : ") + (mv.name || "Ligne") + " (" + sign + Number(mv.changePct || 0).toFixed(1) + " %)",
              body: "Mouvement majeur sur votre ligne (" + (mv.weight || "") + ")."
            });
          }
        }

        var earns = Array.isArray(data.upcomingEarnings) ? data.upcomingEarnings : [];
        for (var e = 0; e < earns.length; e++) {
          var er = earns[e];
          if (!er || !er.id || typeof er.daysLeft !== "number" || er.daysLeft > 2) continue;
          var eid = "earn_" + er.id;
          if (!seenMap[eid]) {
            seenMap[eid] = true;
            list.push(eid);
            pending.push({
              title: "📊 Chiffres " + (er.name || ""),
              body: "Publication prévue le " + (er.dateStr || "") + "."
            });
          }
        }

        var items = Array.isArray(data.items) ? data.items : [];
        for (var i = 0; i < items.length; i++) {
          var it = items[i];
          if (!it || !it.id) continue;
          var nid = "news_" + it.id;
          if (!seenMap[nid]) {
            seenMap[nid] = true;
            list.push(nid);
            pending.push({
              title: "⚡ " + (it.theme || "Marchés"),
              body: it.title || "",
              excerpt: String(it.excerpt || "").trim()
            });
          }
        }

        if (list.length > 200) list = list.slice(list.length - 200);
        return writeSwState({ enabled: true, notifiedIds: list }).then(function() {
          if (!hadSeed || pending.length === 0 || !self.registration || !self.registration.showNotification) return;
          var nTitle = pending.length === 1
            ? pending[0].title
            : ("🔔 Copilote • " + pending.length + " nouveautés");
          var nBody = pending.length === 1
            ? (pending[0].body + (pending[0].excerpt ? ("\n" + pending[0].excerpt) : ""))
            : pending.slice(0, 4).map(function(p) {
                var ex = p.excerpt ? ("\n  " + (p.excerpt.length > 115 ? (p.excerpt.slice(0, 112).trim() + "…") : p.excerpt)) : "";
                return "• " + p.title + " : " + p.body + ex;
              }).join("\n");
          return self.registration.showNotification(nTitle, {
            body: nBody,
            icon: "./icon-192.png",
            badge: "./icon-192.png",
            tag: "copilote-grouped-alert",
            renotify: true
          });
        });
      })
      .catch(function() {});
  });
}

self.addEventListener("install", function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME && k !== STATE_CACHE_NAME && k !== USER_DATA_CACHE; }).map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("message", function(event) {
  var d = event && event.data;
  if (d && d.type === "COPILOTE_SYNC_STATE") {
    event.waitUntil(
      writeSwState({
        enabled: !!d.enabled,
        notifiedIds: Array.isArray(d.notifiedIds) ? d.notifiedIds : []
      })
    );
  }
});

self.addEventListener("periodicsync", function(event) {
  if (event.tag === "copilote-news-sync") {
    event.waitUntil(checkNewsInBackground());
  }
});

self.addEventListener("sync", function(event) {
  if (event.tag === "copilote-news-check") {
    event.waitUntil(checkNewsInBackground());
  }
});

self.addEventListener("fetch", function(event) {
  if (event.request.method !== "GET") return;
  var reqUrl = new URL(event.request.url);
  if (reqUrl.origin !== self.location.origin || reqUrl.pathname.endsWith("/news.json") || reqUrl.pathname.endsWith(".apk")) {
    return;
  }
  event.respondWith(
    fetch(event.request, { cache: "no-cache" })
      .then(function(response) {
        var copy = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, copy);
        });
        return response;
      })
      .catch(function() {
        return caches.match(event.request).then(function(cached) {
          return cached || caches.match("./index.html");
        });
      })
  );
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if ("focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow("./#alerts");
      }
    })
  );
});

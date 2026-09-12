// LIVE Stream Übersicht - Frontend
// Lädt data/events.json (von update_data.py generiert) und zeigt die
// Events als TV-Zeitung mit Tabs "Frei empfangbar" / "Kostenpflichtig".
//
// Hinweis: diese Seite muss über einen Webserver aufgerufen werden
// (nicht per Doppelklick als file://), sonst blockt der Browser den
// fetch() auf data/events.json. Siehe README für ein einfaches
// `python3 -m http.server`-Beispiel.

const state = {
  events: [],
  access: "free",
  day: null, // "YYYY-MM-DD" oder null = alle Tage
  category: "",
  medium: "", // "" = alle, "tv", "radio"
  search: "",
};

const DATA_URL = "../data/events.json";

async function loadData() {
  const content = document.getElementById("content");
  try {
    // Eine per build_preview.py erzeugte Vorschau-Datei bettet die Daten
    // direkt als window.EMBEDDED_DATA ein (funktioniert dann auch offline
    // per Doppelklick, ohne Webserver und ohne fetch()).
    let payload;
    if (window.EMBEDDED_DATA) {
      payload = window.EMBEDDED_DATA;
    } else {
      const res = await fetch(DATA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      payload = await res.json();
    }
    state.events = payload.events || [];
    renderGeneratedAt(payload.generated_at);
    populateCategories();
    renderDayScroller();
    render();
  } catch (err) {
    content.innerHTML = `<p class="empty">Konnte Daten nicht laden (${escapeHtml(
      String(err)
    )}).<br>Wurde <code>update_data.py</code> schon einmal ausgeführt?</p>`;
  }
}

function renderGeneratedAt(iso) {
  const el = document.getElementById("generated-at");
  if (!iso) return;
  const d = new Date(iso);
  el.textContent = `Zuletzt aktualisiert: ${d.toLocaleString("de-DE")}`;
}

function populateCategories() {
  const select = document.getElementById("category-filter");
  const categories = Array.from(
    new Set(state.events.map((e) => e.category).filter(Boolean))
  ).sort((a, b) => a.localeCompare(b, "de"));
  for (const cat of categories) {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = cat;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => {
    state.category = select.value;
    render();
  });
}

function renderDayScroller() {
  const scroller = document.getElementById("day-scroller");
  scroller.innerHTML = "";

  const allChip = document.createElement("button");
  allChip.className = "day-chip active";
  allChip.textContent = "Alle Tage";
  allChip.addEventListener("click", () => selectDay(null, allChip));
  scroller.appendChild(allChip);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = 0; i < 28; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const key = toDateKey(d);
    const chip = document.createElement("button");
    chip.className = "day-chip";
    chip.textContent = d.toLocaleDateString("de-DE", {
      weekday: "short",
      day: "2-digit",
      month: "2-digit",
    });
    chip.addEventListener("click", () => selectDay(key, chip));
    scroller.appendChild(chip);
  }
}

function selectDay(key, chipEl) {
  state.day = key;
  document
    .querySelectorAll(".day-chip")
    .forEach((c) => c.classList.remove("active"));
  chipEl.classList.add("active");
  render();
}

function toDateKey(d) {
  return d.toISOString().slice(0, 10);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      state.access = tab.dataset.access;
      render();
    });
  });

  document.getElementById("search").addEventListener("input", (e) => {
    state.search = e.target.value.trim().toLowerCase();
    render();
  });

  document.getElementById("medium-filter").addEventListener("change", (e) => {
    state.medium = e.target.value;
    render();
  });
}

function filteredEvents() {
  return state.events.filter((e) => {
    if (e.access !== state.access) return false;
    if (state.day) {
      const localKey = new Date(e.start).toISOString().slice(0, 10);
      if (localKey !== state.day) return false;
    }
    if (state.category && e.category !== state.category) return false;
    if (state.medium && (e.medium || "tv") !== state.medium) return false;
    if (state.search) {
      const haystack = `${e.title} ${e.channel} ${e.subtitle || ""}`.toLowerCase();
      if (!haystack.includes(state.search)) return false;
    }
    return true;
  });
}

function groupByDay(events) {
  const groups = new Map();
  for (const e of events) {
    const d = new Date(e.start);
    const key = toDateKey(d);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  }
  return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
}

function render() {
  const content = document.getElementById("content");
  const events = filteredEvents().sort(
    (a, b) => new Date(a.start) - new Date(b.start)
  );

  if (events.length === 0) {
    content.innerHTML = `<p class="empty">Keine Events für diese Auswahl gefunden.</p>`;
    return;
  }

  const groups = groupByDay(events);
  content.innerHTML = groups
    .map(([dayKey, dayEvents]) => {
      const dayLabel = new Date(dayKey).toLocaleDateString("de-DE", {
        weekday: "long",
        day: "2-digit",
        month: "long",
      });
      const cards = dayEvents.map(renderCard).join("");
      return `<section class="day-group">
        <h2 class="day-heading">${escapeHtml(dayLabel)}</h2>
        ${cards}
      </section>`;
    })
    .join("");
}

function renderCard(e) {
  const time = new Date(e.start).toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const accessClass = e.access === "paid" ? "access-paid" : "access-free";
  const accessLabel = e.access === "paid" ? "Kostenpflichtig" : "Frei empfangbar";
  const isRadio = e.medium === "radio";

  return `
    <article class="event-card${isRadio ? " event-card-radio" : ""}">
      <div class="event-time">${time}</div>
      <div class="event-main">
        <p class="event-title">${isRadio ? "📻 " : ""}${escapeHtml(e.title)}</p>
        ${e.subtitle ? `<p class="event-sub">${escapeHtml(e.subtitle)}</p>` : ""}
        <div class="event-meta">
          <span class="badge channel">${escapeHtml(e.channel)}</span>
          ${e.category ? `<span class="badge">${escapeHtml(e.category)}</span>` : ""}
          ${isRadio ? `<span class="badge medium-radio">Radio-Livestream</span>` : ""}
          <span class="badge ${accessClass}">${accessLabel}</span>
        </div>
        ${e.description ? `<p class="event-desc">${escapeHtml(e.description)}</p>` : ""}
      </div>
    </article>
  `;
}

setupTabs();
loadData();

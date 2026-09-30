import * as ui from "../../../utils/ui.js";
const { esc, fmtDateTime, pageHead, table, act, toast, modal } = ui;

/* État des filtres et de la pagination */
const filters = {
  event_type: "",
  success: "",
  search: "",
  date_from: "",
  date_to: "",
};
let page = 0;
const PAGE_SIZE = 50;

/* Cache des événements pour la modale détail */
let cachedEvents = [];

export default {
  title: "Sécurité",
  roles: ["CEO"],
  events: ["security.event", "user.locked", "user.unlocked"],

  async fetch({ api }) {
    const [eventsRes, locked, sessions, stats] = await Promise.all([
      api.get("/api/security/events", {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        event_type: filters.event_type || undefined,
        success: filters.success === "ok" ? true : filters.success === "fail" ? false : undefined,
        search: filters.search || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
      }),
      api.get("/api/security/locked-accounts"),
      api.get("/api/security/active-sessions").catch(() => []),
      api.get("/api/security/stats").catch(() => null),
    ]);

    cachedEvents = eventsRes.items || [];
    return {
      events: cachedEvents,
      total: eventsRes.total || 0,
      locked,
      sessions,
      stats,
    };
  },

  render({ events, total, locked, sessions, stats }) {
    /* ---------- Statistiques ---------- */
    const statsHtml = stats
      ? `
        <div class="stats">
          <div class="stat">
            <div class="stat-label">Connexions réussies</div>
            <div class="stat-value success">${stats.total_success}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Échecs totaux</div>
            <div class="stat-value ${stats.total_failures > 0 ? "danger" : ""}">${stats.total_failures}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Comptes bloqués</div>
            <div class="stat-value ${stats.locked_accounts > 0 ? "danger" : ""}">${stats.locked_accounts}</div>
          </div>
          <div class="stat">
            <div class="stat-label">IP uniques</div>
            <div class="stat-value">${stats.unique_ips}</div>
          </div>
        </div>
      `
      : "";

    /* ---------- Graphique 7 jours ---------- */
    const chartHtml = stats?.daily?.length
      ? (() => {
          const maxVal = Math.max(
            1,
            ...stats.daily.map((d) => Math.max(d.success, d.failures))
          );
          const bars = stats.daily
            .map((d) => {
              const succH = (d.success / maxVal) * 100;
              const failH = (d.failures / maxVal) * 100;
              const dayLabel = new Date(d.date + "T00:00:00").toLocaleDateString("fr-FR", { weekday: "short" });
              const dayNum = new Date(d.date + "T00:00:00").getDate();
              return `
                <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;min-width:0">
                  <div style="height:100px;width:100%;display:flex;align-items:flex-end;justify-content:center;gap:2px;position:relative">
                    <div style="flex:1;max-width:16px;height:${succH}%;background:var(--success);border-radius:3px 3px 0 0;min-height:2px" title="${d.success} succès"></div>
                    <div style="flex:1;max-width:16px;height:${failH}%;background:var(--danger);border-radius:3px 3px 0 0;min-height:2px" title="${d.failures} échecs"></div>
                  </div>
                  <div style="font-size:0.6875rem;color:var(--text-3);text-align:center">
                    ${dayLabel}<br><b style="color:var(--text-2)">${dayNum}</b>
                  </div>
                </div>
              `;
            })
            .join("");

          return `
            <div class="card" style="margin-bottom:1.5rem">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
                <h2 class="card-title" style="margin:0">Activité des 7 derniers jours</h2>
                <div style="display:flex;gap:12px;font-size:0.75rem;color:var(--text-2)">
                  <span><span style="display:inline-block;width:8px;height:8px;background:var(--success);border-radius:2px;margin-right:4px"></span>Succès</span>
                  <span><span style="display:inline-block;width:8px;height:8px;background:var(--danger);border-radius:2px;margin-right:4px"></span>Échecs</span>
                </div>
              </div>
              <div style="display:flex;gap:8px;align-items:flex-end">
                ${bars}
              </div>
            </div>
          `;
        })()
      : "";

    /* ---------- Alertes automatiques ---------- */
    const recentFailures = events.filter(
      (e) =>
        !e.success &&
        new Date(e.created_at) > new Date(Date.now() - 5 * 60 * 1000)
    );

    const alertHtml =
      recentFailures.length >= 10
        ? `
          <div class="card" style="border-color:var(--danger);background:var(--danger-dim);margin-bottom:1.5rem">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="font-size:1.5rem">⚠</div>
              <div>
                <div style="font-weight:700;color:var(--danger)">
                  ${recentFailures.length} échecs de connexion dans les 5 dernières minutes
                </div>
                <div style="font-size:0.8125rem;color:var(--text-2)">
                  Cela peut indiquer une attaque par force brute. Vérifiez les IP concernées.
                </div>
              </div>
            </div>
          </div>
        `
        : "";

    /* ---------- Sessions actives ---------- */
    const sessionsHtml = `
      <div class="card" style="margin-bottom:1.5rem">
        <h2 class="card-title">Sessions actives (${sessions.length})</h2>
        ${
          sessions.length
            ? table(
                [
                  {
                    h: "Utilisateur",
                    cls: "main-cell",
                    cell: (s) => `
                      <div style="display:flex;align-items:center;gap:10px">
                        <div style="width:32px;height:32px;border-radius:50%;background:var(--accent);color:#000;display:grid;place-items:center;font-weight:700;font-size:0.75rem;flex-shrink:0">
                          ${ui.initials(s.name)}
                        </div>
                        <div>
                          <div style="font-weight:600">${esc(s.name)}</div>
                          <div style="font-size:0.75rem;color:var(--text-3)">${esc(s.email)}</div>
                        </div>
                      </div>`,
                  },
                  {
                    h: "Rôle",
                    cell: (s) => `<span class="tag">${esc(s.role)}</span>`,
                  },
                  {
                    h: "Connexions",
                    cls: "num",
                    cell: (s) => `<span class="badge t-g">${s.connections}</span>`,
                  },
                  {
                    h: "",
                    cls: "r",
                    cell: (s) =>
                      `<button class="btn btn-danger btn-sm" data-disconnect="${s.user_id}">Déconnecter</button>`,
                  },
                ],
                sessions
              )
            : `<p style="color:var(--text-2);font-size:0.875rem">Aucune session active.</p>`
        }
      </div>
    `;

    /* ---------- Comptes bloqués ---------- */
    const lockedHtml = locked.length
      ? `
        <div class="card" style="margin-bottom:1.5rem;border-color:var(--danger)">
          <h2 class="card-title" style="color:var(--danger)">
            ⚠ ${locked.length} compte${locked.length > 1 ? "s" : ""} bloqué${locked.length > 1 ? "s" : ""}
          </h2>
          ${table([
            { h: "Nom", cls: "main-cell", cell: (u) => esc(u.name) },
            { h: "Email", cell: (u) => esc(u.email) },
            { h: "Bloqué jusqu'à", cell: (u) => fmtDateTime(u.locked_until) },
            { h: "Tentatives", cls: "num", cell: (u) => u.failed_login_attempts },
            {
              h: "",
              cls: "r",
              cell: (u) => `<button class="btn btn-primary btn-sm" data-unlock="${u.id}">Débloquer</button>`,
            },
          ], locked)}
        </div>
      `
      : "";

    /* ---------- Filtres + pagination ---------- */
    const totalPages = Math.ceil(total / PAGE_SIZE);
    const allEventTypes = [
      ...new Set(events.map((e) => e.event_type)),
    ].sort();

    const filtersHtml = `
      <div class="card" style="margin-bottom:1rem">
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr auto;gap:10px;align-items:end">
          <div class="field">
            <label for="filter-search">Recherche</label>
            <input type="text" id="filter-search" placeholder="Email ou IP…" value="${esc(filters.search)}">
          </div>
          <div class="field">
            <label for="filter-type">Type</label>
            <select id="filter-type">
              <option value="">Tous</option>
              ${allEventTypes.map((t) => `
                <option value="${esc(t)}"${filters.event_type === t ? " selected" : ""}>${esc(t)}</option>
              `).join("")}
            </select>
          </div>
          <div class="field">
            <label for="filter-success">Résultat</label>
            <select id="filter-success">
              <option value="">Tous</option>
              <option value="ok"${filters.success === "ok" ? " selected" : ""}>Succès</option>
              <option value="fail"${filters.success === "fail" ? " selected" : ""}>Échec</option>
            </select>
          </div>
          <div class="field">
            <label for="filter-from">Du</label>
            <input type="date" id="filter-from" value="${esc(filters.date_from)}">
          </div>
          <div class="field">
            <label for="filter-to">Au</label>
            <input type="date" id="filter-to" value="${esc(filters.date_to)}">
          </div>
          <button class="btn btn-secondary btn-sm" id="reset-filters">Réinitialiser</button>
        </div>
      </div>
    `;

    /* ---------- Tableau des événements ---------- */
    const eventsTable = events.length
      ? table(
          [
            {
              h: "Date",
              cell: (e) => `<span style="font-variant-numeric:tabular-nums">${fmtDateTime(e.created_at)}</span>`,
            },
            {
              h: "Type",
              cell: (e) => {
                const colors = {
                  login: "t-c",
                  login_locked_account: "t-m",
                  login_disabled_account: "t-m",
                };
                return `<span class="badge ${colors[e.event_type] || "t-n"}">${esc(e.event_type)}</span>`;
              },
            },
            { h: "Email", cell: (e) => (e.email ? esc(e.email) : `<span class="sub">—</span>`) },
            {
              h: "IP",
              cell: (e) => e.ip_address
                ? `<code style="font-family:monospace;font-size:0.8125rem;background:var(--surface-2);padding:2px 6px;border-radius:4px">${esc(e.ip_address)}</code>`
                : `<span class="sub">—</span>`,
            },
            {
              h: "Résultat",
              cell: (e) =>
                e.success
                  ? `<span class="badge t-g">Succès</span>`
                  : `<span class="badge t-m">Échec</span>`,
            },
            {
              h: "",
              cls: "r",
              cell: (e) => `<button class="btn btn-secondary btn-sm" data-detail="${e.id}">Détail</button>`,
            },
          ],
          events
        )
      : ui.stateHTML.empty(
          "Aucun événement",
          filters.search || filters.event_type || filters.success || filters.date_from || filters.date_to
            ? "Essayez de modifier les filtres."
            : "Les tentatives de connexion apparaîtront ici."
        );

    const paginationHtml = totalPages > 1
      ? `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:1rem;font-size:0.8125rem;color:var(--text-2)">
          <span>
            Page ${page + 1} sur ${totalPages} · ${total} événement${total > 1 ? "s" : ""}
          </span>
          <div style="display:flex;gap:6px">
            <button class="btn btn-secondary btn-sm" id="prev-page" ${page === 0 ? "disabled" : ""}>← Précédent</button>
            <button class="btn btn-secondary btn-sm" id="next-page" ${page >= totalPages - 1 ? "disabled" : ""}>Suivant →</button>
          </div>
        </div>
      `
      : "";

    return (
      pageHead(
        "Sécurité",
        `${total} événement${total > 1 ? "s" : ""} au total`
      ) +
      alertHtml +
      statsHtml +
      chartHtml +
      sessionsHtml +
      lockedHtml +
      filtersHtml +
      `<div class="card">` +
      `<h2 class="card-title">Journal des événements</h2>` +
      eventsTable +
      paginationHtml +
      `</div>`
    );
  },

  bind(view, { events, locked, sessions, stats }, { api, reload }) {
    /* ---------- Filtres ---------- */
    const applyFilters = () => {
      filters.search = view.querySelector("#filter-search")?.value.trim() || "";
      filters.event_type = view.querySelector("#filter-type")?.value || "";
      filters.success = view.querySelector("#filter-success")?.value || "";
      filters.date_from = view.querySelector("#filter-from")?.value || "";
      filters.date_to = view.querySelector("#filter-to")?.value || "";
      page = 0;
      reload();
    };

    let searchTimeout;
    view.querySelector("#filter-search")?.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(applyFilters, 300);
    });

    view.querySelector("#filter-type")?.addEventListener("change", applyFilters);
    view.querySelector("#filter-success")?.addEventListener("change", applyFilters);
    view.querySelector("#filter-from")?.addEventListener("change", applyFilters);
    view.querySelector("#filter-to")?.addEventListener("change", applyFilters);

    view.querySelector("#reset-filters")?.addEventListener("click", () => {
      filters.search = "";
      filters.event_type = "";
      filters.success = "";
      filters.date_from = "";
      filters.date_to = "";
      page = 0;
      reload();
    });

    /* ---------- Pagination ---------- */
    view.querySelector("#prev-page")?.addEventListener("click", () => {
      page = Math.max(0, page - 1);
      reload();
    });
    view.querySelector("#next-page")?.addEventListener("click", () => {
      page++;
      reload();
    });

    /* ---------- Export CSV ---------- */
    view.querySelector("#export-csv")?.addEventListener("click", () => {
      const rows = [
        ["Date", "Type", "Email", "IP", "Résultat"],
        ...events.map((e) => [
          new Date(e.created_at).toISOString(),
          e.event_type,
          e.email || "",
          e.ip_address || "",
          e.success ? "Succès" : "Échec",
        ]),
      ];
      const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
      const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kimia-securite-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast("Export téléchargé");
    });

    /* ---------- Débloquer un compte ---------- */
    view.querySelectorAll("[data-unlock]").forEach((b) =>
      b.addEventListener("click", async () => {
        await act(b, () => api.post(`/api/auth/unlock/${b.dataset.unlock}`), "Compte débloqué");
        reload();
      })
    );

    /* ---------- Déconnecter un utilisateur ---------- */
    view.querySelectorAll("[data-disconnect]").forEach((b) =>
      b.addEventListener("click", async () => {
        const userId = b.dataset.disconnect;
        if (!confirm("Forcer la déconnexion de cet utilisateur ?")) return;
        await act(
          b,
          () => api.post(`/api/security/active-sessions/${userId}/disconnect`),
          "Utilisateur déconnecté"
        );
        reload();
      })
    );

    /* ---------- Détail d'un événement ---------- */
    view.querySelectorAll("[data-detail]").forEach((b) =>
      b.addEventListener("click", () => {
        const event = events.find((e) => e.id === +b.dataset.detail);
        if (!event) return;
        modal({
          title: `Événement #${event.id}`,
          body: `
            <dl style="display:grid;grid-template-columns:140px 1fr;gap:12px 16px">
              <dt style="color:var(--text-2);font-size:0.8125rem">Date</dt>
              <dd style="margin:0">${fmtDateTime(event.created_at)}</dd>
              <dt style="color:var(--text-2);font-size:0.8125rem">Type</dt>
              <dd style="margin:0"><code style="font-family:monospace;font-size:0.8125rem">${esc(event.event_type)}</code></dd>
              <dt style="color:var(--text-2);font-size:0.8125rem">Résultat</dt>
              <dd style="margin:0">${
                event.success
                  ? `<span class="badge t-g">Succès</span>`
                  : `<span class="badge t-m">Échec</span>`
              }</dd>
              <dt style="color:var(--text-2);font-size:0.8125rem">Email</dt>
              <dd style="margin:0">${esc(event.email || "—")}</dd>
              <dt style="color:var(--text-2);font-size:0.8125rem">IP</dt>
              <dd style="margin:0">${esc(event.ip_address || "—")}</dd>
              <dt style="color:var(--text-2);font-size:0.8125rem">User ID</dt>
              <dd style="margin:0">${event.user_id ?? "—"}</dd>
            </dl>
          `,
        });
      })
    );
  },
};
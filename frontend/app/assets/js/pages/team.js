import * as ui from "../../../utils/ui.js";
const { esc, fmtDate, pageHead, table, formModal, act, toast, modal } = ui;

export default {
  title: "Équipe",
  roles: ["CEO", "DA"],
  events: ["activity.assigned", "activity.completed", "user.updated"],

  async fetch({ api, user }) {
    const isCEO = user.role.name === "CEO";
    const [team, roles, skills] = await Promise.all([
      api.get("/api/users/team"),
      isCEO ? api.get("/api/users/roles") : Promise.resolve([]),
      api.get("/api/users/skills").catch(() => []),
    ]);
    return { team, roles, skills, isCEO };
  },

  render({ team, isCEO }, { user }) {
    const isCEOUser = user.role.name === "CEO";
    const active = team.filter((u) => u.is_active).length;
    const cofounders = team.filter((u) => u.ownership_status === "COFOUNDER").length;

    const head = pageHead(
      "Équipe",
      `${team.length} membre${team.length > 1 ? "s" : ""} · ${active} actif${active > 1 ? "s" : ""} · ${cofounders} cofondateur${cofounders > 1 ? "s" : ""}`,
      isCEOUser ? `<button class="btn btn-primary" id="new">Nouveau membre</button>` : ""
    );

    if (!team.length) {
      return head + ui.stateHTML.empty("Aucun membre", "Invitez votre équipe.");
    }

    return head + table(
      [
        {
          h: "Membre",
          cls: "main-cell",
          cell: (u) => `
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;border-radius:50%;background:var(--accent);color:#000;display:grid;place-items:center;font-weight:700;font-size:0.75rem;flex-shrink:0">
                ${ui.initials(u.name)}
              </div>
              <div>
                <div style="font-weight:600">${esc(u.name)}</div>
                <div style="font-size:0.75rem;color:var(--text-3)">${esc(u.email)}</div>
                ${u.phone ? `<div style="font-size:0.75rem;color:var(--text-3)">📱 ${esc(u.phone)}</div>` : ""}
              </div>
            </div>`,
        },
        {
          h: "Rôle",
          cell: (u) => {
            const colors = { CEO: "t-c", DA: "t-y", CM: "t-n" };
            return `<span class="badge ${colors[u.role.name] || "t-n"}">${esc(u.role.name)}</span>`;
          },
        },
        {
          h: "Postes",
          cell: (u) => {
            const positions = u.positions || [];
            if (!positions.length) return `<span style="color:var(--text-3);font-size:0.75rem">—</span>`;
            return positions.map((p) => `<span class="tag">${esc(p.name)}</span>`).join(" ");
          },
        },
        {
          h: "Compétences",
          cell: (u) => {
            const skills = u.skills || [];
            if (!skills.length) return `<span style="color:var(--text-3);font-size:0.75rem">Aucune</span>`;
            const shown = skills.slice(0, 3);
            const rest = skills.length - 3;
            return shown.map((s) => `<span class="tag">${esc(s.name)}</span>`).join(" ") +
                   (rest > 0 ? ` <span class="tag">+${rest}</span>` : "");
          },
        },
        {
          h: "Statut",
          cell: (u) => {
            const badges = [];
            if (u.ownership_status === "COFOUNDER") {
              badges.push(`<span class="badge t-y">Cofondateur</span>`);
            }
            badges.push(
              u.is_active
                ? `<span class="badge t-g">Actif</span>`
                : `<span class="badge t-m">Bloqué</span>`
            );
            return badges.join(" ");
          },
        },
        {
          h: "",
          cls: "r",
          cell: (u) => {
            const actions = [];
            actions.push(`<button class="btn btn-secondary btn-sm" data-skills="${u.id}" title="Compétences">Compétences</button>`);
if (isCEOUser) {
  const isMe = u.id === user.id;

  // Réinitialiser le mot de passe (sauf soi-même)
  if (!isMe) {
    actions.push(`<button class="btn btn-secondary btn-sm" data-reset-password="${u.id}" title="Réinitialiser le mot de passe">🔑</button>`);
  }

  // Bloquer / Débloquer (sauf soi-même)
  if (!isMe) {
    if (u.is_active) {
      actions.push(`<button class="btn btn-danger btn-sm" data-toggle-active="${u.id}" title="Bloquer l'accès">🔒</button>`);
    } else {
      actions.push(`<button class="btn btn-secondary btn-sm" data-toggle-active="${u.id}" title="Débloquer l'accès">🔓</button>`);
    }
  }

  // Supprimer (sauf soi-même)
  if (!isMe) {
    actions.push(`<button class="btn btn-danger btn-sm" data-delete-user="${u.id}" title="Supprimer le compte">❌</button>`);
  }

  // Modifier (toujours autorisé)
  actions.push(`<button class="btn btn-secondary btn-sm" data-edit="${u.id}">Modifier</button>`);
}

            return `<div style="display:flex;gap:6px;justify-content:flex-end">${actions.join("")}</div>`;
          },
        },
      ],
      team
    );
  },

  bind(view, { team, roles, skills }, { api, reload, user }) {
    const isCEOUser = user.role.name === "CEO";

    /* ============================================================
       Compétences
       ============================================================ */
    const openSkills = (member) => {
      const currentSkillIds = new Set((member.skills || []).map((s) => s.id));

      formModal({
        title: `Compétences de ${member.name}`,
        wide: true,
        fields: [],
        submitLabel: "Enregistrer",
        extraHTML: `
          <div class="field field-full">
            <label>Sélectionnez les compétences</label>
            <p class="field-hint" style="margin-bottom:0.75rem">
              Les compétences servent à suggérer les personnes adaptées à chaque activité.
            </p>
            <div id="skills-chips" style="display:flex;flex-wrap:wrap;gap:8px">
              ${skills.length
                ? skills.map((s) => `
                    <label class="skill-chip" style="
                      display:inline-flex;align-items:center;gap:8px;
                      padding:8px 14px;
                      border:1px solid ${currentSkillIds.has(s.id) ? "var(--accent)" : "var(--border)"};
                      border-radius:999px;
                      cursor:pointer;
                      transition:all 150ms;
                      background:${currentSkillIds.has(s.id) ? "var(--accent-dim)" : "transparent"};
                    ">
                      <input type="checkbox" value="${s.id}" ${currentSkillIds.has(s.id) ? "checked" : ""}
                             style="accent-color:var(--accent);width:14px;height:14px">
                      <span style="font-size:0.8125rem;font-weight:500">${esc(s.name)}</span>
                    </label>
                  `).join("")
                : `<p style="color:var(--text-2);font-size:0.8125rem">Aucune compétence disponible.</p>`}
            </div>
          </div>
        `,
        onMount: (el) => {
          el.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
            cb.addEventListener("change", () => {
              const label = cb.closest(".skill-chip");
              if (cb.checked) {
                label.style.background = "var(--accent-dim)";
                label.style.borderColor = "var(--accent)";
              } else {
                label.style.background = "transparent";
                label.style.borderColor = "var(--border)";
              }
            });
          });
        },
        onSubmit: async (data, form) => {
          const checked = [...form.querySelectorAll('#skills-chips input[type="checkbox"]:checked')]
            .map((cb) => Number(cb.value));
          await api.put(`/api/users/${member.id}/skills`, { skill_ids: checked });
          toast("Compétences mises à jour");
          reload();
        },
      });
    };

    view.querySelectorAll("[data-skills]").forEach((b) =>
      b.addEventListener("click", () => {
        openSkills(team.find((u) => u.id === +b.dataset.skills));
      })
    );

    /* ============================================================
       Créer un nouveau membre (CEO)
       ============================================================ */
    if (isCEOUser) {
      view.querySelector("#new")?.addEventListener("click", () => {
        formModal({
          title: "Nouveau membre",
          wide: true,
          fields: [
            { name: "name", label: "Nom complet", required: true, full: true },
            { name: "email", label: "Email", type: "email", required: true, full: true },
            { name: "phone", label: "Téléphone WhatsApp", type: "tel", required: true, full: true,
              placeholder: "+243 097 146 8418",
              hint: "Utilisé pour envoyer les identifiants par WhatsApp." },
            { name: "password", label: "Mot de passe temporaire", type: "password", required: true, full: true,
              hint: "8 caractères minimum. Le membre pourra le changer." },
            { name: "role_id", label: "Rôle", type: "select", required: true,
              options: roles.map((r) => ({ v: r.id, l: r.name })) },
            { name: "ownership_status", label: "Statut", type: "select",
              options: [
                { v: "COLLABORATOR", l: "Collaborateur" },
                { v: "COFOUNDER", l: "Cofondateur" },
              ] },
          ],
          values: { ownership_status: "COLLABORATOR" },
          submitLabel: "Créer le membre",
          onSubmit: async (v) => {
            await api.post("/api/users", v);
            toast("Membre créé. Transmettez-lui ses identifiants.");
            reload();
          },
        });
      });
    }

    /* ============================================================
       Modifier un membre (CEO)
       ============================================================ */
    if (isCEOUser) {
      view.querySelectorAll("[data-edit]").forEach((b) =>
        b.addEventListener("click", () => {
          const member = team.find((u) => u.id === +b.dataset.edit);
          formModal({
            title: `Modifier ${member.name}`,
            fields: [
              { name: "name", label: "Nom complet", required: true, full: true },
              { name: "email", label: "Email", type: "email", required: true, full: true },
              { name: "phone", label: "Téléphone WhatsApp", type: "tel", required: true, full: true },
              { name: "role_id", label: "Rôle", type: "select", required: true,
                options: roles.map((r) => ({ v: r.id, l: r.name })) },
              { name: "ownership_status", label: "Statut", type: "select",
                options: [
                  { v: "COLLABORATOR", l: "Collaborateur" },
                  { v: "COFOUNDER", l: "Cofondateur" },
                ] },
              { name: "is_active", label: "Actif", type: "select",
                options: [
                  { v: "true", l: "Oui" },
                  { v: "false", l: "Non" },
                ] },
            ],
            values: {
              name: member.name,
              email: member.email,
              phone: member.phone || "",
              role_id: member.role.id,
              ownership_status: member.ownership_status,
              is_active: String(member.is_active),
            },
            onSubmit: async (v) => {
              await api.patch(`/api/users/${member.id}`, {
                name: v.name,
                email: v.email,
                phone: v.phone,
                role_id: Number(v.role_id),
                ownership_status: v.ownership_status,
                is_active: v.is_active === "true",
              });
              toast("Membre modifié");
              reload();
            },
          });
        })
      );
    }

    /* ============================================================
       Réinitialiser le mot de passe (CEO)
       ============================================================ */
    const openSendPassword = (member, password) => {
      const loginUrl = `${window.location.origin}/app/login.html`;
      const message =
        `Bonjour ${member.name.split(" ")[0]},\n\n` +
        `Voici ton nouveau mot de passe Kimia : ${password}\n\n` +
        `Connecte-toi : ${loginUrl}\n` +
        `Change-le dès que possible dans "Mon profil".\n\n` +
        `— ${user.name}`;

      modal({
        title: "Mot de passe réinitialisé",
        body: `
          <div style="text-align:center;margin-bottom:1.5rem">
            <div style="width:56px;height:56px;border-radius:50%;background:var(--accent-dim);color:var(--accent);display:grid;place-items:center;margin:0 auto 1rem;border:1px solid var(--accent)">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <h3 style="font-weight:700;font-size:1.125rem;margin-bottom:0.5rem">Mot de passe réinitialisé</h3>
            <p style="color:var(--text-2);font-size:0.875rem">Transmettez-le à <b>${esc(member.name)}</b> :</p>
          </div>

          <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:12px;padding:1rem;margin-bottom:1.5rem;text-align:center">
            <div style="font-size:0.75rem;color:var(--text-3);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem">Mot de passe</div>
            <div style="font-family:monospace;font-size:1.25rem;font-weight:700;color:var(--accent);user-select:all" id="pwd-display">${esc(password)}</div>
            <button class="btn btn-secondary btn-sm" id="copy-pwd" style="margin-top:0.75rem">📋 Copier</button>
          </div>

          <div style="display:flex;flex-direction:column;gap:8px">
            <button class="btn btn-primary" id="send-whatsapp" style="justify-content:center">
              📱 Envoyer par WhatsApp
            </button>
            <button class="btn btn-secondary" id="send-email" style="justify-content:center">
              📧 Envoyer par Email
            </button>
          </div>
        `,
        onMount: (el, close) => {
          el.querySelector("#copy-pwd").onclick = () => {
            navigator.clipboard.writeText(password);
            toast("Mot de passe copié");
          };

          el.querySelector("#send-whatsapp").onclick = () => {
            if (!member.phone) {
              toast("Ce membre n'a pas de numéro WhatsApp", "err");
              return;
            }
            const cleanPhone = member.phone.replace(/\D/g, "");
            const url = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message)}`;
            window.open(url, "_blank");
          };

          el.querySelector("#send-email").onclick = () => {
            if (!member.email) {
              toast("Ce membre n'a pas d'email", "err");
              return;
            }
            const subject = "Nouveau mot de passe Kimia";
            const url = `mailto:${member.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(message)}`;
            window.location.href = url;
          };
        },
      });
    };

    view.querySelectorAll("[data-reset-password]").forEach((b) =>
      b.addEventListener("click", () => {
        const member = team.find((u) => u.id === +b.dataset.resetPassword);

        formModal({
          title: `Réinitialiser le mot de passe de ${member.name}`,
          fields: [
            { name: "new_password", label: "Nouveau mot de passe", type: "password", required: true, full: true,
              placeholder: "8 caractères minimum" },
            { name: "confirm_password", label: "Confirmer", type: "password", required: true, full: true },
          ],
          submitLabel: "Réinitialiser",
          onSubmit: async (v) => {
            if (v.new_password !== v.confirm_password) {
              toast("Les mots de passe ne correspondent pas", "err");
              return false;
            }
            if (v.new_password.length < 8) {
              toast("Minimum 8 caractères", "err");
              return false;
            }

            try {
              await api.post(`/api/users/${member.id}/reset-password`, {
                new_password: v.new_password,
              });
              // Ouvre la modale de transmission
              setTimeout(() => openSendPassword(member, v.new_password), 300);
            } catch (err) {
              toast(err.message || "Erreur", "err");
              return false;
            }
          },
        });
      })
    );

    /* ============================================================
       Bloquer / Débloquer (CEO)
       ============================================================ */
    if (isCEOUser) {
      view.querySelectorAll("[data-toggle-active]").forEach((b) =>
        b.addEventListener("click", async () => {
          const member = team.find((u) => u.id === +b.dataset.toggleActive);
          const action = member.is_active ? "bloquer" : "débloquer";
          if (!confirm(`Voulez-vous vraiment ${action} l'accès de ${member.name} ?`)) return;
          await act(
            b,
            () => api.post(`/api/users/${member.id}/toggle-active`),
            member.is_active ? `${member.name} a été bloqué` : `${member.name} a été débloqué`
          );
          reload();
        })
      );
    }

    /* ============================================================
       Supprimer un compte (CEO)
       ============================================================ */
    if (isCEOUser) {
      view.querySelectorAll("[data-delete-user]").forEach((b) =>
        b.addEventListener("click", async () => {
          const member = team.find((u) => u.id === +b.dataset.deleteUser);

          const c1 = confirm(
            `⚠️ Supprimer définitivement ${member.name} ?\n\n` +
            `Le compte sera désactivé et anonymisé.\n` +
            `L'historique (activités, messages) sera conservé.`
          );
          if (!c1) return;

          const c2 = prompt(`Tapez "SUPPRIMER" pour confirmer :`);
          if (c2 !== "SUPPRIMER") {
            toast("Suppression annulée", "err");
            return;
          }

          await act(b, () => api.del(`/api/users/${member.id}`), `${member.name} a été supprimé`);
          reload();
        })
      );
    }
  },
};
import * as ui from "../../../utils/ui.js";
const { esc, fmtMoney, pageHead, table, formModal, toast } = ui;

const FIELDS = [
  { name: "name", label: "Nom", required: true, full: true },
  { name: "description", label: "Description", type: "textarea", full: true },
  {
    name: "base_price",
    label: "Prix de base",
    type: "number",
    hint: "Laisser vide si le prix n'est pas fixé pour cette prestation.",
  },
  {
    name: "is_active",
    label: "Actif",
    type: "select",
    options: [
      { v: "true", l: "Oui" },
      { v: "false", l: "Non" },
    ],
  },
];

export default {
  title: "Services",
  roles: ["CEO", "DA"],
  events: ["service.updated"],
  fetch: ({ api }) => api.get("/api/services"),

  render(services) {
    const active = services.filter((s) => s.is_active).length;
    const withPrice = services.filter((s) => s.base_price != null).length;

    const head = pageHead(
      "Services",
      `${services.length} prestation${services.length > 1 ? "s" : ""} · ${active} active${active > 1 ? "s" : ""} · ${withPrice} avec prix`
    );

    if (!services.length) {
      return head + ui.stateHTML.empty(
        "Aucun service",
        "Les services sont créés via le seed ou l'administration."
      );
    }

    return head + table(
      [
        { h: "Nom", cls: "main-cell", cell: (s) => esc(s.name) },
        {
          h: "Description",
          cell: (s) =>
            s.description
              ? `<span class="sub">${esc(s.description.slice(0, 80))}${s.description.length > 80 ? "…" : ""}</span>`
              : `<span class="sub">—</span>`,
        },
        {
          h: "Prix de base",
          cls: "num",
          cell: (s) =>
            s.base_price != null
              ? `<b>${fmtMoney(s.base_price)}</b>`
              : `<span class="sub">Non défini</span>`,
        },
        {
          h: "Statut",
          cell: (s) =>
            s.is_active
              ? `<span class="badge t-g">Actif</span>`
              : `<span class="badge">Inactif</span>`,
        },
        {
          h: "",
          cls: "r",
          cell: (s) => `<button class="btn btn-secondary btn-sm" data-edit="${s.id}">Modifier</button>`,
        },
      ],
      services
    );
  },

  bind(view, services, { api, reload }) {
    const open = (service) => {
      const values = {
        name: service.name,
        description: service.description || "",
        base_price: service.base_price ?? "",
        is_active: String(service.is_active),
      };

      formModal({
        title: `Modifier « ${service.name} »`,
        fields: FIELDS,
        values,
        submitLabel: "Enregistrer",
        onSubmit: async (v) => {
          const payload = {
            ...v,
            is_active: v.is_active === "true",
            base_price:
              v.base_price === "" || v.base_price === null ? null : Number(v.base_price),
          };
          await api.patch(`/api/services/${service.id}`, payload);
          toast("Service modifié");
          reload();
        },
      });
    };

    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () =>
        open(services.find((s) => s.id === +b.dataset.edit))
      )
    );
  },
};
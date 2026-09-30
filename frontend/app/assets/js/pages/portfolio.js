import * as ui from "../../../utils/ui.js";
const { esc, fmtDate, pageHead, table, formModal, act, confirmBox, toast } = ui;

const MAX_IMAGE_MB = 10;
let selectedImage = null;

const FIELDS = [
  { name: "title", label: "Titre", required: true, full: true },
  { name: "category", label: "Catégorie", required: true, placeholder: "Ex: Photographie, Graphisme…" },
  { name: "client_name", label: "Client (optionnel)" },
  { name: "description", label: "Description", type: "textarea", full: true },
  { name: "external_link", label: "Lien externe (optionnel)", full: true, placeholder: "https://…" },
  { name: "display_order", label: "Ordre d'affichage", type: "number", value: 0 },
  {
    name: "is_published",
    label: "Publié sur le site public",
    type: "select",
    options: [
      { v: "true", l: "Oui" },
      { v: "false", l: "Non" },
    ],
  },
];

export default {
  title: "Réalisations",
  roles: ["CEO", "DA"],
  events: ["portfolio.created", "portfolio.updated", "portfolio.deleted"],
  fetch: ({ api }) => api.get("/api/portfolio"),

  render(items) {
    const published = items.filter((i) => i.is_published).length;
    const head = pageHead(
      "Réalisations",
      `${items.length} élément${items.length > 1 ? "s" : ""} · ${published} publié(s)`,
      `<button class="btn btn-primary" id="new">Nouvelle réalisation</button>`
    );

    if (!items.length) {
      return head + ui.stateHTML.empty(
        "Aucune réalisation",
        "Ajoutez vos premiers projets pour les afficher sur le site public."
      );
    }

    return head + table(
      [
        {
          h: "Aperçu",
          cell: (i) =>
            i.image_path
              ? `<img src="${esc((window.KIMIA_API || "") + i.image_path)}" alt="" style="width:48px;height:48px;border-radius:8px;object-fit:cover;background:var(--surface-2)">`
              : `<div style="width:48px;height:48px;border-radius:8px;background:var(--surface-2);display:grid;place-items:center;color:var(--text-3);font-size:0.75rem">—</div>`,
        },
        { h: "Titre", cls: "main-cell", cell: (i) => esc(i.title) },
        { h: "Catégorie", cell: (i) => `<span class="tag">${esc(i.category)}</span>` },
        {
          h: "Statut",
          cell: (i) =>
            i.is_published
              ? `<span class="badge t-g">Publié</span>`
              : `<span class="badge">Brouillon</span>`,
        },
        { h: "Ordre", cls: "num", cell: (i) => i.display_order },
        {
          h: "",
          cls: "r",
          cell: (i) => `
            <div style="display:flex;gap:6px;justify-content:flex-end">
              <button class="btn btn-secondary btn-sm" data-edit="${i.id}">Modifier</button>
              <button class="btn btn-danger btn-sm" data-rm="${i.id}">Supprimer</button>
            </div>`,
        },
      ],
      items
    );
  },

  bind(view, items, { api, reload }) {
    const open = (item) => {
      selectedImage = null;
      const currentImage = item?.image_path || null;

      formModal({
        title: item ? "Modifier la réalisation" : "Nouvelle réalisation",
        wide: true,
        fields: FIELDS,
        values: item
          ? { ...item, is_published: String(item.is_published) }
          : { is_published: "true", display_order: 0 },
        submitLabel: item ? "Enregistrer" : "Créer",
        extraHTML: `
          <div class="field field-full" style="margin-top:0.5rem">
            <label>Image de couverture</label>
            <div style="display:flex;gap:1rem;align-items:flex-start">
              <div id="img-preview" style="width:120px;height:80px;border-radius:8px;background:var(--surface-2);background-size:cover;background-position:center;flex-shrink:0;border:1px solid var(--border);${
                currentImage ? `background-image:url('${(window.KIMIA_API || "") + currentImage}');` : ""
              }"></div>
              <div style="flex:1">
                <label class="btn btn-secondary" style="cursor:pointer;display:inline-flex">
                  Choisir une image
                  <input id="img-input" type="file" accept="image/*" hidden>
                </label>
                <div class="field-hint" style="margin-top:6px">
                  Formats : JPEG, PNG, WebP, GIF, SVG · Max ${MAX_IMAGE_MB} Mo
                </div>
              </div>
            </div>
          </div>
        `,
        onMount: (form) => {
          const input = form.querySelector("#img-input");
          const preview = form.querySelector("#img-preview");

          input?.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
              toast(`Image trop volumineuse (max ${MAX_IMAGE_MB} Mo)`, "err");
              e.target.value = "";
              return;
            }

            const reader = new FileReader();
            reader.onload = (ev) => {
              preview.style.backgroundImage = `url('${ev.target.result}')`;
            };
            reader.readAsDataURL(file);

            try {
              const result = await api.upload("/api/portfolio/upload", {}, file);
              selectedImage = result.image_path;
              toast("Image téléchargée");
            } catch (err) {
              toast(err.message || "Erreur d'upload", "err");
            }
          });
        },
        onSubmit: async (v) => {
          const payload = {
            title: v.title,
            category: v.category,
            client_name: v.client_name || null,
            description: v.description || null,
            external_link: v.external_link || null,
            display_order: v.display_order ?? 0,
            is_published: v.is_published === "true",
            image_path: selectedImage ?? currentImage,
          };
          if (item) await api.patch(`/api/portfolio/${item.id}`, payload);
          else await api.post("/api/portfolio", payload);
          toast(item ? "Réalisation modifiée" : "Réalisation créée");
          reload();
        },
      });
    };

    view.querySelector("#new")?.addEventListener("click", () => open());

    view.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => open(items.find((i) => i.id === +b.dataset.edit)))
    );

    view.querySelectorAll("[data-rm]").forEach((b) =>
      b.addEventListener("click", async () => {
        const item = items.find((i) => i.id === +b.dataset.rm);
        if (!(await confirmBox(`Supprimer « ${item.title} » ?`, "Supprimer"))) return;
        await act(b, () => api.del(`/api/portfolio/${item.id}`), "Réalisation supprimée");
        reload();
      })
    );
  },
};
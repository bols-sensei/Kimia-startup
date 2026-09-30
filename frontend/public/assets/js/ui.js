/* Composants UI réutilisables pour le site public */

export const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));

/* Icônes par catégorie */
export const CATEGORY_ICONS = {
  "Photographie": '<path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/>',
  "Vidéo": '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
  "Conception graphique": '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 011.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
  "Développement web": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
  "Communication digitale": '<path d="M3 11l18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 11-5.8-1.6"/>',
  "Invitations digitales": '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>',
};

export const DEFAULT_ICON = '<circle cx="12" cy="12" r="10"/>';

/* Toast */
export function toast(msg, kind = "ok") {
  const root = document.getElementById("toasts");
  if (!root) return;

  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = msg;
  root.append(t);

  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transition = "opacity 200ms";
    setTimeout(() => t.remove(), 200);
  }, kind === "err" ? 5000 : 3000);
}

/* Formatage prix */
export const formatPrice = (n) => {
  if (n === null || n === undefined || n === "") return "Sur devis";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(n)) + " F";
};
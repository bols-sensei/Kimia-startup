/* Point d'entrée du site public */

import { api } from "./api.js";
import { esc, CATEGORY_ICONS, DEFAULT_ICON, toast } from "./ui.js";

/* ============================================================
   État
   ============================================================ */
let services = [];
let categories = [];
let currentService = null;
let currentSlide = 0;
let slides = [];

/* ============================================================
   Année dans le footer
   ============================================================ */
document.getElementById("year").textContent = new Date().getFullYear();

/* ============================================================
   Menu mobile
   ============================================================ */
const menuBtn = document.getElementById("menu-btn");
const mobileNav = document.getElementById("mobile-nav");

menuBtn?.addEventListener("click", () => {
  mobileNav.classList.toggle("open");
});

mobileNav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => mobileNav.classList.remove("open"));
});

/* ============================================================
   Chargement du catalogue (section Services)
   ============================================================ */
async function loadCatalogue() {
  const track = document.getElementById("carousel-track");
  const dots = document.getElementById("carousel-dots");
  if (!track) return;

  try {
    const [cats, svcs] = await Promise.all([
      api.getCategories(),
      api.getServices(),
    ]);

    categories = cats;
    services = svcs;

    const grouped = categories
      .map((cat) => ({
        ...cat,
        services: services.filter((s) => s.category_id === cat.id),
      }))
      .filter((c) => c.services.length > 0);

    if (!grouped.length) {
      track.innerHTML = `
        <div class="empty" style="width:100%;text-align:center;padding:3rem">
          <div class="empty-title">Aucune prestation disponible</div>
          <div class="empty-text">Revenez bientôt.</div>
        </div>`;
      return;
    }

    slides = grouped;

    track.innerHTML = grouped
      .map(
        (cat) => `
        <div class="carousel-slide">
          <div class="category-card">
            <div class="category-header">
              <div class="category-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  ${CATEGORY_ICONS[cat.name] || DEFAULT_ICON}
                </svg>
              </div>
              <h3 class="category-title">${esc(cat.name)}</h3>
              <span class="category-count">${cat.services.length}</span>
            </div>
            <div class="services">
              ${cat.services
                .map(
                  (s) => `
                <button type="button" class="service-row" data-service-id="${s.id}">
                  <div class="service-info">
                    <span class="service-name">${esc(s.name)}</span>
                  </div>
                  <span class="service-cta">Choisir →</span>
                </button>
              `
                )
                .join("")}
            </div>
          </div>
        </div>
      `
      )
      .join("");

    dots.innerHTML = grouped
      .map((_, i) => `<button class="carousel-dot${i === 0 ? " active" : ""}" data-slide="${i}" aria-label="Slide ${i + 1}"></button>`)
      .join("");

    track.querySelectorAll("[data-service-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const serviceId = +el.dataset.serviceId;
        const service = services.find((s) => s.id === serviceId);

        toast(`Service sélectionné : ${service.name}`, "ok");

        document.getElementById("demande").scrollIntoView({ behavior: "smooth" });

        setTimeout(() => selectService(serviceId), 600);
      });
    });

    setupCarousel();

  } catch (e) {
    track.innerHTML = `
      <div class="error-box" style="width:100%;text-align:center;padding:3rem">
        <p>Impossible de charger le catalogue.</p>
        <button class="btn btn-secondary" onclick="location.reload()">Réessayer</button>
      </div>`;
  }
}

/* ============================================================
   Carrousel de la section Services
   ============================================================ */
function setupCarousel() {
  const track = document.getElementById("carousel-track");
  const prevBtn = document.getElementById("carousel-prev");
  const nextBtn = document.getElementById("carousel-next");
  const dots = document.getElementById("carousel-dots");

  const updateCarousel = () => {
    if (!track || !track.children.length) return;

    const width = window.innerWidth;
    let visible = 3;
    if (width <= 1000) visible = 2;
    if (width <= 640) visible = 1;

    const maxSlide = Math.max(0, slides.length - visible);
    currentSlide = Math.min(currentSlide, maxSlide);

    const slideWidth = track.children[0]?.offsetWidth || 0;
    const gap = 20;
    const offset = currentSlide * (slideWidth + gap);

    track.style.transform = `translateX(-${offset}px)`;

    dots?.querySelectorAll(".carousel-dot").forEach((dot, i) => {
      dot.classList.toggle("active", i === currentSlide);
    });

    if (prevBtn) prevBtn.disabled = currentSlide === 0;
    if (nextBtn) nextBtn.disabled = currentSlide >= maxSlide;
  };

  prevBtn?.addEventListener("click", () => {
    currentSlide = Math.max(0, currentSlide - 1);
    updateCarousel();
  });

  nextBtn?.addEventListener("click", () => {
    const width = window.innerWidth;
    let visible = 3;
    if (width <= 1000) visible = 2;
    if (width <= 640) visible = 1;
    const maxSlide = Math.max(0, slides.length - visible);

    currentSlide = Math.min(maxSlide, currentSlide + 1);
    updateCarousel();
  });

  dots?.querySelectorAll(".carousel-dot").forEach((dot) => {
    dot.addEventListener("click", () => {
      currentSlide = +dot.dataset.slide;
      updateCarousel();
    });
  });

  let touchStart = 0;
  let touchEnd = 0;

  track?.addEventListener("touchstart", (e) => {
    touchStart = e.changedTouches[0].screenX;
  }, { passive: true });

  track?.addEventListener("touchend", (e) => {
    touchEnd = e.changedTouches[0].screenX;
    const diff = touchStart - touchEnd;
    if (Math.abs(diff) < 50) return;
    if (diff > 0) nextBtn?.click();
    else prevBtn?.click();
  }, { passive: true });

  window.addEventListener("resize", updateCarousel);
  updateCarousel();
}

/* ============================================================
   Chargement du portfolio (masqué si vide)
   ============================================================ */
async function loadPortfolio() {
  const section = document.getElementById("portfolio-section");
  const container = document.getElementById("portfolio-grid");
  if (!container || !section) return;

  try {
    const items = await api.getPortfolio();
    const base = window.KIMIA_API || "";

    if (!items.length) {
      section.hidden = true;
      return;
    }

    section.hidden = false;

    container.innerHTML = items
      .map(
        (item) => `
        <article class="portfolio-card">
          ${
            item.image_path
              ? `<div class="portfolio-image" style="background-image: url('${esc(base + item.image_path)}')"></div>`
              : `<div class="portfolio-image" style="background: linear-gradient(135deg, #1a1a1a, #262626);"></div>`
          }
          <div class="portfolio-body">
            <div class="portfolio-tag">${esc(item.category)}</div>
            <h3 class="portfolio-title">${esc(item.title)}</h3>
            ${item.description ? `<p class="portfolio-desc">${esc(item.description)}</p>` : ""}
          </div>
        </article>
      `
      )
      .join("");

  } catch {
    section.hidden = true;
  }
}

/* ============================================================
   Formulaire — Étape 1 : choix du service (carrousel)
   ============================================================ */
function renderServiceSelector() {
  const form = document.getElementById("request-form");
  if (!form) return;

  const grouped = categories
    .map((cat) => ({
      ...cat,
      services: services.filter((s) => s.category_id === cat.id),
    }))
    .filter((c) => c.services.length > 0);

  form.innerHTML = `
    <div class="form-step">
      <div class="form-step-progress">
        <div class="form-step-dot active"></div>
        <div class="form-step-dot"></div>
      </div>

      <div class="form-step-header">
        <div class="form-step-num">1</div>
        <div>
          <h3 class="form-step-title">Choisissez une prestation</h3>
          <p class="form-step-sub">Sélectionnez ce qui correspond à votre projet.</p>
        </div>
      </div>

      <div class="form-carousel-wrapper">
        <button type="button" class="form-carousel-nav form-carousel-prev" id="form-carousel-prev" aria-label="Précédent">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>

        <div class="form-carousel">
          <div class="form-carousel-track" id="form-carousel-track">
            ${grouped
              .map(
                (cat) => `
              <div class="form-carousel-slide">
                <div class="form-category-card">
                  <div class="form-category-header">
                    <div class="form-category-icon">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        ${CATEGORY_ICONS[cat.name] || DEFAULT_ICON}
                      </svg>
                    </div>
                    <h4 class="form-category-title">${esc(cat.name)}</h4>
                    <span class="form-category-count">${cat.services.length}</span>
                  </div>
                  <div class="form-services">
                    ${cat.services
                      .map(
                        (s) => `
                      <button type="button" class="form-service-row" data-service-id="${s.id}">
                        <span class="form-service-name">${esc(s.name)}</span>
                        <span class="form-service-arrow">→</span>
                      </button>
                    `
                      )
                      .join("")}
                  </div>
                </div>
              </div>
            `
              )
              .join("")}
          </div>
        </div>

        <button type="button" class="form-carousel-nav form-carousel-next" id="form-carousel-next" aria-label="Suivant">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>

      <div class="form-carousel-dots" id="form-carousel-dots"></div>
    </div>
  `;

  const dots = form.querySelector("#form-carousel-dots");
  dots.innerHTML = grouped
    .map((_, i) => `<button type="button" class="form-carousel-dot${i === 0 ? " active" : ""}" data-slide="${i}" aria-label="Slide ${i + 1}"></button>`)
    .join("");

  setupFormCarousel(grouped.length);

  form.querySelectorAll("[data-service-id]").forEach((el) => {
    el.addEventListener("click", () => selectService(+el.dataset.serviceId));
  });
}

/* ============================================================
   Carrousel du formulaire
   ============================================================ */
function setupFormCarousel(totalSlides) {
  const track = document.getElementById("form-carousel-track");
  const prevBtn = document.getElementById("form-carousel-prev");
  const nextBtn = document.getElementById("form-carousel-next");
  const dots = document.getElementById("form-carousel-dots");

  let formSlide = 0;

  const updateFormCarousel = () => {
    if (!track || !track.children.length) return;

    const width = window.innerWidth;
    let visible = 3;
    if (width <= 1000) visible = 2;
    if (width <= 640) visible = 1;

    const maxSlide = Math.max(0, totalSlides - visible);
    formSlide = Math.min(formSlide, maxSlide);

    const slideWidth = track.children[0]?.offsetWidth || 0;
    const gap = 20;
    const offset = formSlide * (slideWidth + gap);

    track.style.transform = `translateX(-${offset}px)`;

    dots?.querySelectorAll(".form-carousel-dot").forEach((dot, i) => {
      dot.classList.toggle("active", i === formSlide);
    });

    if (prevBtn) prevBtn.disabled = formSlide === 0;
    if (nextBtn) nextBtn.disabled = formSlide >= maxSlide;
  };

  prevBtn?.addEventListener("click", () => {
    formSlide = Math.max(0, formSlide - 1);
    updateFormCarousel();
  });

  nextBtn?.addEventListener("click", () => {
    const width = window.innerWidth;
    let visible = 3;
    if (width <= 1000) visible = 2;
    if (width <= 640) visible = 1;
    const maxSlide = Math.max(0, totalSlides - visible);

    formSlide = Math.min(maxSlide, formSlide + 1);
    updateFormCarousel();
  });

  dots?.querySelectorAll(".form-carousel-dot").forEach((dot) => {
    dot.addEventListener("click", () => {
      formSlide = +dot.dataset.slide;
      updateFormCarousel();
    });
  });

  let touchStart = 0;
  let touchEnd = 0;

  track?.addEventListener("touchstart", (e) => {
    touchStart = e.changedTouches[0].screenX;
  }, { passive: true });

  track?.addEventListener("touchend", (e) => {
    touchEnd = e.changedTouches[0].screenX;
    const diff = touchStart - touchEnd;
    if (Math.abs(diff) < 50) return;
    if (diff > 0) nextBtn?.click();
    else prevBtn?.click();
  }, { passive: true });

  window.addEventListener("resize", updateFormCarousel);
  updateFormCarousel();
}

/* ============================================================
   Sélection d'un service
   ============================================================ */
function selectService(serviceId) {
  currentService = services.find((s) => s.id === serviceId);
  if (currentService) renderDynamicForm();
}

/* ============================================================
   Formulaire — Étape 2 : champs dynamiques
   ============================================================ */
function renderDynamicForm() {
  const form = document.getElementById("request-form");
  if (!form || !currentService) return;

  const svc = currentService;
  const fields = svc.form_fields || [];
  const eventTypes = svc.event_types || [];

  form.innerHTML = `
    <div class="form-step">
      <div class="form-step-progress">
        <div class="form-step-dot active"></div>
        <div class="form-step-dot active"></div>
      </div>

      <div class="form-step-header">
        <div class="form-step-num">2</div>
        <div style="flex:1">
          <h3 class="form-step-title">${esc(svc.name)}</h3>
          <p class="form-step-sub">Répondez aux questions ci-dessous.</p>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" id="back-btn">← Retour</button>
      </div>

      <div class="form-fields">
        ${
          eventTypes.length
            ? `
          <div class="field field-full">
            <label for="event_type_id">Type d'événement <span class="required">*</span></label>
            <select id="event_type_id" name="event_type_id" required>
              <option value="">— Choisir —</option>
              ${eventTypes.map((et) => `<option value="${et.id}">${esc(et.name)}</option>`).join("")}
            </select>
          </div>
        `
            : ""
        }

        <div class="form-row">
          ${fields.map((f) => renderField(f)).join("")}
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" id="submit-btn">
          Envoyer ma demande
        </button>
      </div>
    </div>
  `;

  document.getElementById("back-btn").onclick = () => {
    currentService = null;
    renderServiceSelector();
  };

  form.onsubmit = handleSubmit;
}

/* ============================================================
   Rendu d'un champ
   ============================================================ */
function renderField(f) {
  const ff = f.form_field;
  const id = "field_" + ff.id;
  const required = f.is_required ? " required" : "";
  const reqLabel = f.is_required ? ' <span class="required">*</span>' : "";
  const full = ["textarea"].includes(ff.field_type) ? " field-full" : "";

  let control;

  if (ff.field_type === "textarea") {
    control = `<textarea id="${id}" name="${id}"${required}></textarea>`;
  } else if (ff.field_type === "select") {
    const choices = ff.options?.choices || [];
    control = `<select id="${id}" name="${id}"${required}>
      <option value="">— Choisir —</option>
      ${choices.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}
    </select>`;
  } else {
    const typeMap = {
      text: "text",
      email: "email",
      tel: "tel",
      number: "number",
      date: "date",
      time: "time",
    };
    const type = typeMap[ff.field_type] || "text";
    control = `<input id="${id}" name="${id}" type="${type}"${required}>`;
  }

  return `
    <div class="field${full}" data-label="${esc(ff.label)}">
      <label for="${id}">${esc(ff.label)}${reqLabel}</label>
      ${control}
    </div>
  `;
}

/* ============================================================
   Soumission du formulaire
   ============================================================ */
async function handleSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById("submit-btn");

  btn.disabled = true;
  btn.textContent = "Envoi en cours…";

  try {
    let clientName = "";
    let clientEmail = "";
    let clientPhone = "";
    const formData = {};

    form.querySelectorAll(".field[data-label]").forEach((el) => {
      const label = el.dataset.label;
      const input = el.querySelector("input, select, textarea");
      if (!input || !input.value.trim()) return;

      const value = input.value.trim();
      formData[label] = value;

      const lower = label.toLowerCase();
      if (lower.includes("nom") && !clientName) clientName = value;
      if (lower.includes("email") && !clientEmail) clientEmail = value;
      if ((lower.includes("téléphone") || lower.includes("phone")) && !clientPhone) clientPhone = value;
    });

    const missing = [];
    currentService.form_fields.forEach((f) => {
      if (!f.is_required) return;
      const label = f.form_field.label;
      if (!formData[label]) missing.push(label);
    });

    if (missing.length) {
      toast(`Champs obligatoires : ${missing.join(", ")}`, "err");
      btn.disabled = false;
      btn.textContent = "Envoyer ma demande";
      return;
    }

    if (!clientName) {
      toast("Veuillez renseigner votre nom.", "err");
      btn.disabled = false;
      btn.textContent = "Envoyer ma demande";
      return;
    }

    const eventTypeSelect = form.querySelector("#event_type_id");
    const payload = {
      client_name: clientName,
      client_phone: clientPhone || "Non renseigné",
      client_email: clientEmail || null,
      service_id: currentService.id,
      event_type_id: eventTypeSelect && eventTypeSelect.value ? +eventTypeSelect.value : null,
      form_data: formData,
      notes: null,
    };

    await api.submitRequest(payload);

    form.innerHTML = `
      <div class="success-box">
        <div class="success-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <h3 class="success-title">Demande envoyée !</h3>
        <p class="success-text">
          Merci ${esc(clientName)} ! Nous avons bien reçu votre demande pour <b>${esc(currentService.name)}</b>.<br>
          Nous vous recontactons sous 24h ouvrées par WhatsApp ou email.
        </p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
          <a href="https://wa.me/2430971468418" target="_blank" rel="noopener" class="btn btn-primary">
            Nous écrire sur WhatsApp
          </a>
          <button type="button" class="btn btn-secondary" id="reset-btn">
            Envoyer une autre demande
          </button>
        </div>
      </div>
    `;

    document.getElementById("reset-btn").onclick = () => {
      currentService = null;
      renderServiceSelector();
    };

    toast("Votre demande a bien été envoyée", "ok");

  } catch (err) {
    toast(err.message || "Une erreur est survenue", "err");
    btn.disabled = false;
    btn.textContent = "Envoyer ma demande";
  }
}

/* ============================================================
   Init
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const [cats, svcs] = await Promise.all([
      api.getCategories(),
      api.getServices(),
    ]);

    categories = cats;
    services = svcs;

    await loadCatalogue();
    await loadPortfolio();
    renderServiceSelector();

  } catch (e) {
    console.error(e);
    const container = document.getElementById("catalogue");
    if (container) {
      container.innerHTML = `
        <div class="error-box">
          <p>Impossible de charger le catalogue.</p>
          <button class="btn btn-secondary" onclick="location.reload()">Réessayer</button>
        </div>`;
    }
  }
}); 
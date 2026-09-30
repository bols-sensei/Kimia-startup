// URL de l'API. Servi par FastAPI (:8000) => même origine ; sinon http://localhost:8000.
window.KIMIA_API = location.port === "8000" ? location.origin : "http://localhost:8000";
window.KIMIA_CURRENCY = "USD";

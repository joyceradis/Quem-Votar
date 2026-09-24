(() => {
  "use strict";

  const MEASUREMENT_ID = "G-2KY1FDKV88";
  const CANONICAL_ORIGIN = "https://joyceradis.github.io";
  const PROJECT_BASE_PATH = "/Quem-Votar/";
  const SAFE_ROUTES = Object.freeze({
    "": "Quem Votar? · Espírito Santo 2026",
    "index.html": "Quem Votar? · Espírito Santo 2026",
    "candidatos.html": "Candidaturas · Quem Votar?",
    "candidato.html": "Entenda esta candidatura · Quem Votar?",
    "comparar.html": "Comparar · Quem Votar?",
    "temas.html": "Temas · Quem Votar?",
    "sobre.html": "Sobre o projeto · Quem Votar?",
    "apoio.html": "Apoie o Quem Votar?",
  });

  function canonicalRoot() {
    return {
      location: CANONICAL_ORIGIN + PROJECT_BASE_PATH,
      title: SAFE_ROUTES[""],
      route: "",
    };
  }

  function sanitizePage(rawUrl) {
    let current;
    try {
      current = new URL(rawUrl);
    } catch (_) {
      return canonicalRoot();
    }

    if (current.origin !== CANONICAL_ORIGIN) return canonicalRoot();
    if (!current.pathname.startsWith(PROJECT_BASE_PATH)) return canonicalRoot();

    const relativePath = current.pathname.slice(PROJECT_BASE_PATH.length);
    if (!Object.prototype.hasOwnProperty.call(SAFE_ROUTES, relativePath)) {
      return canonicalRoot();
    }

    return {
      location: CANONICAL_ORIGIN + PROJECT_BASE_PATH + relativePath,
      title: SAFE_ROUTES[relativePath],
      route: relativePath,
    };
  }

  function sanitizeReferrer(rawReferrer) {
    if (!rawReferrer) return "";

    let referrer;
    try {
      referrer = new URL(rawReferrer);
    } catch (_) {
      return "";
    }

    if (referrer.origin !== CANONICAL_ORIGIN) return "";
    if (!referrer.pathname.startsWith(PROJECT_BASE_PATH)) return "";

    const relativePath = referrer.pathname.slice(PROJECT_BASE_PATH.length);
    if (!Object.prototype.hasOwnProperty.call(SAFE_ROUTES, relativePath)) return "";

    return CANONICAL_ORIGIN + PROJECT_BASE_PATH + relativePath;
  }

  const safePage = sanitizePage(window.location.href);
  const safeReferrer = sanitizeReferrer(document.referrer);

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };

  window.gtag("js", new Date());
  window.gtag("config", MEASUREMENT_ID, {
    send_page_view: false,
    page_location: safePage.location,
    page_referrer: safeReferrer,
    page_title: safePage.title,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });
  window.gtag("event", "page_view", {
    page_location: safePage.location,
    page_referrer: safeReferrer,
    page_title: safePage.title,
  });

  const loader = document.createElement("script");
  loader.async = true;
  loader.src =
    "https://www.googletagmanager.com/gtag/js?id=" +
    encodeURIComponent(MEASUREMENT_ID);
  loader.dataset.qvGa4 = "privacy";
  document.head.appendChild(loader);
})();

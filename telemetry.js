(() => {
  "use strict";

  const MEASUREMENT_ID = "G-2KY1FDKV88";
  const SAFE_TITLES = Object.freeze({
    "": "Quem Votar? · Espírito Santo 2026",
    "index.html": "Quem Votar? · Espírito Santo 2026",
    "candidatos.html": "Candidaturas · Quem Votar?",
    "candidato.html": "Entenda esta candidatura · Quem Votar?",
    "comparar.html": "Comparar · Quem Votar?",
    "temas.html": "Temas · Quem Votar?",
    "sobre.html": "Sobre o projeto · Quem Votar?",
    "apoio.html": "Apoie o Quem Votar?",
  });

  function getBaseUrl() {
    const script = document.currentScript;
    if (script && script.src) return new URL("./", script.src);
    return new URL("./", window.location.href);
  }

  function getSafePage() {
    const base = getBaseUrl();
    const current = new URL(window.location.href);
    let relativePath = "";

    if (current.pathname.startsWith(base.pathname)) {
      relativePath = current.pathname.slice(base.pathname.length);
    }

    if (!Object.prototype.hasOwnProperty.call(SAFE_TITLES, relativePath)) {
      relativePath = "";
    }

    const safeLocation = new URL(relativePath, base);
    safeLocation.search = "";
    safeLocation.hash = "";

    return {
      location: safeLocation.toString(),
      title: SAFE_TITLES[relativePath],
    };
  }

  const safePage = getSafePage();

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };

  window.gtag("js", new Date());
  window.gtag("config", MEASUREMENT_ID, {
    send_page_view: false,
    page_location: safePage.location,
    page_referrer: "",
    page_title: safePage.title,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    ignore_referrer: true,
  });
  window.gtag("event", "page_view", {
    page_location: safePage.location,
    page_referrer: "",
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

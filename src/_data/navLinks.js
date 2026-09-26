// Fonte única da navegação principal — antes, esta mesma lista de 4 links
// estava copiada à mão em 6 arquivos HTML (desktop nav + drawer, em cada
// página) e em telemetry.js (SAFE_ROUTES). Qualquer mudança de rótulo/rota
// exigia editar tudo isso em uníssono. Agora existe uma vez só.
module.exports = [
  { key: "candidatos", href: "candidatos.html?cargo=federal", label: "Candidatos" },
  { key: "temas", href: "temas.html", label: "Assuntos" },
  { key: "comparar", href: "comparar.html", label: "Comparar" },
  { key: "sobre", href: "sobre.html", label: "Como funciona" },
];

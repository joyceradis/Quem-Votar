import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateProfileUIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")

    def test_primary_question_order_and_secondary_electoral_data(self):
        app = self.app
        today = app.index('id="faz-hoje"')
        proposes = app.index('id="vai-fazer"')
        impact = app.index('id="impacto"')
        electoral = app.index('id="dados-eleitorais"')
        sources = app.index('id="fontes"')
        self.assertLess(today, proposes)
        self.assertLess(proposes, impact)
        self.assertLess(impact, electoral)
        self.assertLess(electoral, sources)
        hero_start = app.index('<section class="profile-hero">')
        jump_start = app.index('<nav class="profile-jump"', hero_start)
        self.assertNotIn("${electoralFactsContent}", app[hero_start:jump_start])
        self.assertIn('class="profile-now"', app[hero_start:jump_start])

    def test_proposal_section_preserves_each_evidence_and_explicit_absence(self):
        block = self.app.split("  const promisesContent=", 1)[1].split("  const impactContent=", 1)[0]
        self.assertIn("thematicEvidence.map", block)
        self.assertIn("item.statement||item.quote_or_summary", block)
        self.assertIn("evidenceTypeLabel(item.evidence_type)", block)
        self.assertIn("item.source_publisher", block)
        self.assertIn("item.published_at", block)
        self.assertIn("Abrir fonte", block)
        self.assertIn("Ainda não há proposta, declaração ou atuação temática integrada com fonte para esta candidatura.", block)
        self.assertIn("Isso não significa que a pessoa não tenha posição ou proposta.", block)
        self.assertIn("O site não usa partido, profissão ou histórico para adivinhar posição.", block)

    def test_impact_is_evidence_gated_taxonomic_and_non_value_judging(self):
        practical = self.app.split("function practicalAreas(candidate){", 1)[1].split("function evidenceTypeLabel", 1)[0]
        self.assertIn("topicEvidence(candidate)", practical)
        self.assertIn("new Set", practical)
        self.assertIn(".filter(Boolean)", practical)
        self.assertNotIn("candidate.party", practical)
        self.assertNotIn("candidate.occupation", practical)
        block = self.app.split("  const impactContent=", 1)[1].split("  const historyContent=", 1)[0]
        self.assertIn("thematicEvidence.length", block)
        self.assertIn("impactTopics.length", block)
        self.assertIn("topic.life_areas", block)
        self.assertIn("Áreas relacionadas aos temas documentados nesta ficha.", block)
        self.assertIn("não são previsão de benefício, prejuízo ou efeito individual", block)
        self.assertIn("Há um tema documentado, mas a base ainda não permite explicar um impacto prático específico sem fazer inferências.", block)
        self.assertIn("Ainda não há informação suficiente na base para relacionar esta candidatura a impactos práticos documentados.", block)
        self.assertNotIn("Essas são áreas que a proposta pode atingir.", block)
        lowered = block.lower()
        for forbidden in ("beneficia você", "prejudica você", "melhor candidato", "pior candidato", "recomenda votar"):
            self.assertNotIn(forbidden, lowered)

    def test_mobile_profile_controls_remain_large_and_single_column(self):
        self.assertIn("/* Candidate profile — issue #127 */", self.styles)
        self.assertIn(".profile-now", self.styles)
        self.assertIn("@media(max-width:620px){.profile-actions{display:grid;grid-template-columns:1fr;width:100%}", self.styles)
        self.assertIn(".profile-actions button{width:100%;min-height:48px}", self.styles)


if __name__ == "__main__":
    unittest.main()

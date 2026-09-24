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

    def test_proposal_section_is_prospective_only_and_has_short_fail_safe_copy(self):
        helpers = self.app.split("function normalizedEvidenceType", 1)[1].split("function hasInstitutional", 1)[0]
        self.assertIn('type==="proposta"||type==="declaracao"', helpers)
        self.assertIn('normalizedEvidenceType(item?.evidence_type)==="atuacao"', helpers)

        block = self.app.split("  const promisesContent=", 1)[1].split("  const impactContent=", 1)[0]
        self.assertIn("prospectiveThematicEvidence.map", block)
        self.assertNotIn("thematicEvidence.map", block)
        self.assertIn("item.statement||item.quote_or_summary", block)
        self.assertIn("evidenceTypeLabel(item.evidence_type)", block)
        self.assertIn("item.source_publisher", block)
        self.assertIn("item.published_at", block)
        self.assertIn("Abrir fonte", block)
        self.assertIn("Ainda não há proposta ou declaração documentada nesta base.", block)
        self.assertIn("Ausência de registro não significa ausência de proposta.", block)
        self.assertNotIn("partido", block.lower())
        self.assertNotIn("profissão", block.lower())

    def test_impact_is_prospective_evidence_gated_taxonomic_and_non_value_judging(self):
        practical = self.app.split("function practicalAreasFromEvidence(evidence){", 1)[1].split("function evidenceTypeLabel", 1)[0]
        self.assertIn("new Set", practical)
        self.assertIn(".filter(Boolean)", practical)
        self.assertNotIn("candidate.party", practical)
        self.assertNotIn("candidate.occupation", practical)

        profile_setup = self.app.split("  const institutionalEvidence=", 1)[1].split("  const socialName=", 1)[0]
        self.assertIn("prospectiveTopicEvidence(candidate)", profile_setup)
        self.assertIn("documentedActionEvidence(candidate)", profile_setup)
        self.assertIn("practicalAreasFromEvidence(prospectiveThematicEvidence)", profile_setup)

        block = self.app.split("  const impactContent=", 1)[1].split("  const electoralHistoryContent=", 1)[0]
        self.assertIn("prospectiveThematicEvidence.length", block)
        self.assertIn("impactTopics.length", block)
        self.assertIn("topic.life_areas", block)
        self.assertIn("Áreas relacionadas às propostas e declarações documentadas nesta ficha.", block)
        self.assertIn("não são previsão de benefício, prejuízo ou efeito individual", block)
        self.assertIn("Há proposta ou declaração documentada, mas o tema ainda não permite relacionar impactos práticos sem fazer inferências.", block)
        self.assertIn("Ainda não há proposta ou declaração documentada suficiente para relacionar impactos práticos.", block)
        lowered = block.lower()
        for forbidden in ("beneficia você", "prejudica você", "melhor candidato", "pior candidato", "recomenda votar"):
            self.assertNotIn(forbidden, lowered)

    def test_documented_action_moves_to_history_and_all_sources_are_preserved(self):
        history = self.app.split("  const actionHistoryContent=", 1)[1].split("  const sources=", 1)[0]
        self.assertIn("actionThematicEvidence.map", history)
        self.assertIn("Atuação pública documentada", history)
        self.assertIn("item.statement||item.quote_or_summary", history)
        self.assertIn("item.source_publisher", history)
        self.assertIn("item.published_at", history)
        self.assertIn("Abrir fonte", history)

        sources = self.app.split("  const sources=", 1)[1].split("  const profileCompareIds=", 1)[0]
        self.assertIn("thematicEvidence.filter", sources)
        self.assertNotIn("prospectiveThematicEvidence.filter", sources)

    def test_mobile_profile_controls_remain_large_and_single_column(self):
        self.assertIn("/* Candidate profile — issue #127 */", self.styles)
        self.assertIn(".profile-now", self.styles)
        self.assertIn("@media(max-width:620px){.profile-actions{display:grid;grid-template-columns:1fr;width:100%}", self.styles)
        self.assertIn(".profile-actions button{width:100%;min-height:48px}", self.styles)


if __name__ == "__main__":
    unittest.main()

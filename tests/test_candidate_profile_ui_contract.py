import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateProfileUIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = (ROOT / "src" / "js" / "pages" / "profile.js").read_text(encoding="utf-8")
        cls.evidence = (ROOT / "src" / "js" / "core" / "evidence.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "src" / "styles" / "pages" / "profile.css").read_text(encoding="utf-8")

    def test_primary_question_order_and_secondary_electoral_data(self):
        app = self.profile
        positions = [app.index(f'id="{name}"') for name in (
            "faz-hoje", "vai-fazer", "impacto", "historico", "dados-eleitorais", "fontes"
        )]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('renderHero(candidate, kind, name, socialName, currentActivityText)', app)
        self.assertIn('class="profile-now"', app)

    def test_proposal_section_is_prospective_only_and_has_short_fail_safe_copy(self):
        self.assertIn('return type === "proposta" || type === "declaracao";', self.evidence)
        self.assertIn('normalizedEvidenceType(item?.evidence_type) === "atuacao"', self.evidence)
        block = self.profile.split("function renderProposes(prospective)", 1)[1].split("function renderImpact", 1)[0]
        for token in (
            "prospective.length", "item.statement || item.quote_or_summary",
            "evidenceMetaLine(item)", "sourceLink(item)",
            "Nenhuma proposta ou declaração documentada nesta base ainda.",
            "Sem registro não é o mesmo que sem proposta.",
        ):
            self.assertIn(token, block)
        self.assertNotIn("candidate.occupation", block)

    def test_impact_is_prospective_evidence_gated_taxonomic_and_non_value_judging(self):
        practical = self.evidence.split("export function practicalAreasFromEvidence", 1)[1].split(
            "export function practicalAreas(candidate)", 1
        )[0]
        self.assertIn("new Set", practical)
        self.assertIn(".filter(Boolean)", practical)
        self.assertNotIn("candidate.party", practical)
        self.assertNotIn("candidate.occupation", practical)

        setup = self.profile.split("const thematicEvidence =", 1)[1].split("const assets =", 1)[0]
        for token in (
            "prospectiveTopicEvidence(candidate)",
            "documentedActionEvidence(candidate)",
            "practicalAreasFromEvidence(prospective)",
        ):
            self.assertIn(token, setup)

        block = self.profile.split("function renderImpact(prospective, impactTopics)", 1)[1].split(
            "function renderHistory", 1
        )[0]
        for token in (
            "prospective.length", "impactTopics.length", "topic.life_areas",
            "Áreas relacionadas às propostas e declarações documentadas nesta ficha.",
            "não são previsão de benefício, prejuízo ou efeito individual",
            "Há proposta ou declaração registrada, mas ainda não há áreas relacionadas nesta base.",
            "Ainda não há registros suficientes nesta ficha para relacionar áreas da vida pública.",
        ):
            self.assertIn(token, block)
        lowered = block.lower()
        for forbidden in ("beneficia você", "prejudica você", "melhor candidato", "pior candidato", "recomenda votar"):
            self.assertNotIn(forbidden, lowered)

    def test_documented_action_moves_to_history_and_all_sources_are_preserved(self):
        history = self.profile.split("function renderHistory(historyItems, actionEvidence, candidate)", 1)[1].split(
            "function renderElectoralData", 1
        )[0]
        for token in (
            "actionEvidence.length", "Atuação pública documentada",
            "item.statement || item.quote_or_summary",
            "evidenceMetaLine(item)", "sourceLink(item)",
        ):
            self.assertIn(token, history)
        meta = self.profile.split("function evidenceMetaLine(item)", 1)[1].split("function sourceLink", 1)[0]
        self.assertIn("evidenceTypeLabel(item.evidence_type)", meta)
        self.assertIn("item.source_publisher", meta)
        self.assertIn("item.published_at", meta)

        link = self.profile.split("function sourceLink(item)", 1)[1].split("function renderHero", 1)[0]
        self.assertIn("Abrir fonte", link)

        sources = self.profile.split("function collectSources", 1)[1].split("function showMessage", 1)[0]
        self.assertIn("...thematicEvidence", sources)
        self.assertIn("evidenceTypeLabel(item.evidence_type)", sources)

    def test_mobile_profile_controls_remain_large_and_single_column(self):
        css = self.styles
        for token in (
            ".profile-now", "@media (max-width: 620px)",
            ".profile-actions {", "grid-template-columns: 1fr;", "min-height: 48px;",
        ):
            self.assertIn(token, css)


if __name__ == "__main__":
    unittest.main()

import json
import hashlib
import unittest
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "staging" / "issue161-majoritarian-proposal-sources.json"
DRAFTS = ROOT / "data" / "staging" / "issue161-majoritarian-proposal-drafts.json"
POLICY_TOPICS = ROOT / "data" / "reference" / "policy-topics.json"
GOVERNORS = ROOT / "data" / "generated" / "candidates-governador.json"
SENATORS = ROOT / "data" / "generated" / "candidates-senador.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class MajoritarianProposalStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources_doc = load(SOURCES)
        cls.drafts_doc = load(DRAFTS)
        cls.sources = cls.sources_doc["sources"]
        cls.drafts = cls.drafts_doc["drafts"]
        cls.governors = load(GOVERNORS)
        cls.senators = load(SENATORS)
        cls.topic_ids = {item["id"] for item in load(POLICY_TOPICS)["topics"]}

    def test_staging_covers_exactly_the_16_majoritarian_candidates(self):
        expected = {
            str(item["tse_id"])
            for item in self.governors + self.senators
        }
        source_ids = {str(item["candidate_id"]) for item in self.sources}
        draft_ids = {str(item["candidate_id"]) for item in self.drafts}

        self.assertEqual(16, len(expected))
        self.assertEqual(expected, source_ids)
        self.assertEqual(expected, draft_ids)

    def test_each_candidate_has_one_first_pass_source_and_draft(self):
        source_candidate_ids = [str(item["candidate_id"]) for item in self.sources]
        draft_candidate_ids = [str(item["candidate_id"]) for item in self.drafts]

        self.assertEqual(len(source_candidate_ids), len(set(source_candidate_ids)))
        self.assertEqual(len(draft_candidate_ids), len(set(draft_candidate_ids)))

    def test_drafts_reference_existing_sources_and_policy_topics(self):
        source_ids = {item["source_id"] for item in self.sources}

        for draft in self.drafts:
            with self.subTest(draft_id=draft["draft_id"]):
                self.assertIn(draft["source_id"], source_ids)
                self.assertIn(draft["topic_id"], self.topic_ids)
                self.assertIn(draft["evidence_type"], {"proposta", "declaração"})
                self.assertEqual("pending", draft["review_status"])
                self.assertEqual("not_promoted", draft["promotion_status"])
                self.assertNotEqual("verified", draft["verification_status"])

    def test_governor_sources_preserve_verified_official_package_provenance(self):
        tse_resource = (
            "https://dadosabertos.tse.jus.br/dataset/candidatos-2026/"
            "resource/c1df9a86-90df-4f1f-a604-a0b55a1ffcae"
        )
        governor_ids = {str(item["tse_id"]) for item in self.governors}
        governor_sources = [
            item for item in self.sources if str(item["candidate_id"]) in governor_ids
        ]

        self.assertEqual(5, len(governor_sources))
        for source in governor_sources:
            with self.subTest(source_id=source["source_id"]):
                self.assertEqual(tse_resource, source["source_url"])
                self.assertEqual(
                    "official_tse_package",
                    source["retrieval"]["mode"],
                )
                retrieval = source["retrieval"]
                self.assertEqual(
                    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
                    "proposta_governo/proposta_governo_2026_ES.zip",
                    retrieval["url"],
                )
                self.assertEqual(
                    f"ES/2026ES{source['candidate_id']}_01.pdf",
                    retrieval["member_path"],
                )
                for key in ("package_sha256", "document_sha256", "content_sha256"):
                    self.assertRegex(retrieval[key], r"^[a-f0-9]{64}$")
                self.assertEqual("official_document_captured", retrieval["hash_status"])
                self.assertEqual(
                    "public_mirror_of_tse_document",
                    source["previous_retrieval"]["mode"],
                )

    def test_publication_proposal_preserves_support_without_approving_drafts(self):
        proposal = load(ROOT / "data/staging/tse-q2-publication-proposal.json")
        captured = {
            item["draft_id"]: item
            for item in load(ROOT / "data/staging/topic-evidence-drafts.json")["drafts"]
        }
        normalize = lambda value: " ".join(unicodedata.normalize("NFKD", value).casefold().split())
        self.assertEqual("pending_independent_review_and_human_approval", proposal["status"])
        self.assertEqual(
            {str(item["tse_id"]) for item in self.governors},
            {item["proposed_entry"]["candidate_id"] for item in proposal["entries"]},
        )
        self.assertEqual(5, len(proposal["entries"]))
        for item in proposal["entries"]:
            with self.subTest(draft_id=item["draft_id"]):
                draft = captured[item["draft_id"]]
                self.assertEqual("pending", item["review_status"])
                self.assertEqual("pending", draft["review_status"])
                self.assertEqual(item["proposed_entry"]["candidate_id"], draft["candidate_id"])
                self.assertIn(normalize(item["support_text"]), normalize(draft["raw_excerpt"]))
                self.assertEqual(
                    hashlib.sha256(draft["raw_excerpt"].encode("utf-8")).hexdigest(),
                    draft["content_sha256"],
                )
                self.assertEqual(draft["source_sha256"], item["source_origin"]["document_sha256"])
                self.assertEqual(proposal["package_sha256"], item["source_origin"]["package_sha256"])
                self.assertTrue(all(1 <= page <= draft["page_count"] for page in draft["document_pages"]))

    def test_staging_declares_human_gate_and_is_not_ui_canonical(self):
        self.assertEqual("staging_only", self.sources_doc["status"])
        self.assertEqual("staging_only", self.drafts_doc["status"])
        self.assertIn("revisão humana", self.drafts_doc["canonical_gate"].lower())


if __name__ == "__main__":
    unittest.main()

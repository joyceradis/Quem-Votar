import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.js"


def run_profile(candidate, topics=None):
    app = APP_PATH.read_text(encoding="utf-8")
    harness = r"""
const vm=require("vm");
const candidate=JSON.parse(process.argv[1]);
const topics=JSON.parse(process.argv[2]);

const elements={
  profileMount:{className:"",innerHTML:""}
};
const storage=new Map();
const context={
  console,
  URL,
  URLSearchParams,
  Intl,
  Date,
  encodeURIComponent,
  setTimeout:()=>0,
  clearTimeout:()=>{},
  location:{
    search:"?id="+encodeURIComponent(String(candidate.tse_id))+"&cargo="+(candidate._kind||"estadual"),
    href:"https://example.test/candidato.html?id="+encodeURIComponent(String(candidate.tse_id))+"&cargo="+(candidate._kind||"estadual")
  },
  history:{replaceState:()=>{}},
  navigator:{clipboard:{writeText:async()=>{}}},
  localStorage:{
    getItem:key=>storage.has(key)?storage.get(key):null,
    setItem:(key,value)=>storage.set(key,String(value)),
    removeItem:key=>storage.delete(key),
    clear:()=>storage.clear()
  },
  window:{addEventListener:()=>{}},
  document:{
    title:"",
    body:{dataset:{page:""},classList:{add:()=>{},remove:()=>{}}},
    documentElement:{dataset:{}},
    getElementById:id=>elements[id]||null,
    querySelectorAll:()=>[],
    querySelector:()=>null,
    addEventListener:()=>{}
  }
};
context.globalThis=context;
vm.createContext(context);
const source=require("fs").readFileSync(process.argv[3],"utf8")+
  "\n;globalThis.__qv={currentActivity,practicalAreas,normalizeCompareIds,comparisonState,initProfile,hasInstitutional};";
vm.runInContext(source,context,{filename:"app.js"});
context.loadCore=async()=>({
  federal:candidate._kind==="federal"?[candidate]:[],
  estadual:candidate._kind==="federal"?[]:[candidate],
  meta:{collected_at:"2026-09-23T12:00:00-03:00"}
});
context.getJSON=async()=>[];
context.loadTopics=async()=>({version:"test",topics});
(async()=>{
  await context.__qv.initProfile();
  process.stdout.write(JSON.stringify({
    html:elements.profileMount.innerHTML,
    current:context.__qv.currentActivity(candidate,candidate._kind||"estadual"),
    normalized:context.__qv.normalizeCompareIds(["1","1","2","3","4"]),
    comparison:context.__qv.comparisonState(["1","2","3"]),
    institutional:context.__qv.hasInstitutional(candidate)
  }));
})().catch(error=>{console.error(error);process.exit(1);});
"""
    result = subprocess.run(
        ["node", "-e", harness, json.dumps(candidate), json.dumps(topics or []), str(APP_PATH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class CandidateProfileBehaviorTest(unittest.TestCase):
    def base_candidate(self, **overrides):
        candidate = {
            "tse_id": "1",
            "_kind": "estadual",
            "ballot_name": "Pessoa Teste",
            "full_name": "Pessoa Teste da Silva",
            "party": "ABC",
            "number": "12345",
            "occupation": "Médica",
            "registration_status": "DEFERIDO",
            "topic_evidence": [],
            "institutional_evidence": [],
            "institutional_history": None,
            "previous_elections": [],
        }
        candidate.update(overrides)
        return candidate

    def test_occupation_only_does_not_become_current_activity(self):
        output = run_profile(self.base_candidate())
        html = output["html"]
        self.assertEqual(output["current"], "Atuação atual ainda não confirmada nesta base")
        self.assertNotIn("Trabalho informado ao TSE", html)
        self.assertIn("Não encontramos atuação pública atual confirmada nesta base.", html)
        self.assertIn('id="dados-eleitorais"', html)
        self.assertIn("Ocupação declarada", html)
        self.assertIn("Médica", html)

    def test_current_mandate_is_rendered_as_current_fact(self):
        output = run_profile(self.base_candidate(current_mandate={"party": "ABC", "status": "em exercício"}))
        html = output["html"]
        self.assertEqual(output["current"], "Mandato atual confirmado")
        self.assertIn('<span>Hoje</span><strong>Mandato atual confirmado</strong>', html)
        self.assertNotIn("Não encontramos atuação pública atual confirmada nesta base.", html)

    def test_institutional_evidence_without_current_mandate_does_not_claim_today(self):
        evidence = [{
            "reference_date": "2025",
            "institution": "ALES",
            "legislature": "2025",
            "type": "atuação",
            "source": {"url": "https://example.test/fonte"},
        }]
        output = run_profile(self.base_candidate(institutional_evidence=evidence))
        today = output["html"].split('id="faz-hoje"', 1)[1].split('id="vai-fazer"', 1)[0]
        self.assertIn("Não encontramos atuação pública atual confirmada nesta base.", today)
        self.assertNotIn("ALES", today)

    def test_institutional_history_without_current_mandate_is_recognized_but_not_current(self):
        # Caso A (#157): há histórico institucional real, mas nenhum mandato atual.
        # hasInstitutional deve reconhecer o registro sem inventar atividade atual.
        history = {
            "chamber_id": "204521",
            "profile_url": "https://www.camara.leg.br/deputados/204521",
            "history": [
                {"legislature_id": "56", "party": "ABC", "condition": "Titular", "status": "Fim de mandato"}
            ],
            "external_mandates": [
                {"office": "Vereador", "uf": "ES", "municipality": "Vitória", "party": "ABC", "start_year": 2017, "end_year": 2020}
            ],
        }
        output = run_profile(self.base_candidate(institutional_history=history))
        html = output["html"]
        today = html.split('id="faz-hoje"', 1)[1].split('id="vai-fazer"', 1)[0]
        sources = html.split('id="fontes"', 1)[1]

        self.assertTrue(output["institutional"])
        self.assertEqual(output["current"], "Atuação atual ainda não confirmada nesta base")
        self.assertIn("Não encontramos atuação pública atual confirmada nesta base.", today)
        self.assertIn("https://www.camara.leg.br/deputados/204521", sources)

    def test_institutional_history_object_without_records_stays_absent(self):
        # institutional_history é um objeto estruturado, não um array: presença do
        # objeto sozinha não pode virar "há atuação institucional" sem history/external_mandates.
        output = run_profile(self.base_candidate(institutional_history={"chamber_id": "1"}))
        self.assertFalse(output["institutional"])

    def test_no_institutional_history_and_no_current_mandate_stays_absent(self):
        # Caso B (#157): nenhum campo presente — ausência permanece ausência.
        output = run_profile(self.base_candidate())
        self.assertFalse(output["institutional"])

    def test_current_mandate_marks_institutional_as_present(self):
        # Caso C (#157): comportamento existente com mandato atual é preservado.
        output = run_profile(self.base_candidate(current_mandate={"party": "ABC", "status": "em exercício"}))
        self.assertTrue(output["institutional"])

    def test_empty_topic_evidence_has_fail_safe_proposal_and_impact_states(self):
        html = run_profile(self.base_candidate())["html"]
        self.assertIn("Ainda não há proposta ou declaração documentada nesta base.", html)
        self.assertIn("Ausência de registro não significa ausência de proposta.", html)
        self.assertIn("Ainda não há proposta ou declaração documentada suficiente para relacionar impactos práticos.", html)

    def test_unknown_topic_id_does_not_invent_impact(self):
        evidence = [{
            "topic_id": "tema-desconhecido",
            "evidence_type": "proposta",
            "statement": "Texto documentado",
            "source_publisher": "Fonte",
            "published_at": "2026-09-01",
            "source_url": "https://example.test/evidencia",
        }]
        html = run_profile(self.base_candidate(topic_evidence=evidence))["html"]
        self.assertIn("tema-desconhecido", html)
        self.assertIn("Há proposta ou declaração documentada, mas o tema ainda não permite relacionar impactos práticos sem fazer inferências.", html)

    def test_action_only_stays_out_of_proposal_and_impact_but_remains_accessible(self):
        evidence = [{
            "topic_id": "direitos",
            "evidence_type": "atuação",
            "statement": "Atuação histórica documentada",
            "source_publisher": "Câmara",
            "published_at": "2025-05-01",
            "source_url": "https://example.test/acao",
        }]
        topics = [{"id": "direitos", "label": "Direitos", "life_areas": ["cidadania"]}]
        html = run_profile(self.base_candidate(topic_evidence=evidence), topics)["html"]
        proposal = html.split('id="vai-fazer"', 1)[1].split('id="impacto"', 1)[0]
        impact = html.split('id="impacto"', 1)[1].split('id="historico"', 1)[0]
        history = html.split('id="historico"', 1)[1].split('id="dados-eleitorais"', 1)[0]
        sources = html.split('id="fontes"', 1)[1]

        self.assertIn("Ainda não há proposta ou declaração documentada nesta base.", proposal)
        self.assertNotIn("Atuação histórica documentada", proposal)
        self.assertNotIn("Direitos", impact)
        self.assertIn("Ainda não há proposta ou declaração documentada suficiente para relacionar impactos práticos.", impact)
        self.assertIn("Atuação pública documentada", history)
        self.assertIn("Atuação histórica documentada", history)
        self.assertIn("https://example.test/acao", history)
        self.assertIn("https://example.test/acao", sources)
        self.assertNotIn("Médica", proposal)
        self.assertNotIn("ABC", proposal)

    def test_proposal_only_drives_proposal_and_impact(self):
        evidence = [{
            "topic_id": "saude",
            "evidence_type": "proposta",
            "statement": "Propõe ampliar atendimento",
            "source_publisher": "Fonte oficial",
            "published_at": "2026-09-01",
            "source_url": "https://example.test/proposta",
        }]
        topics = [{"id": "saude", "label": "Saúde", "life_areas": ["SUS", "atenção básica"]}]
        html = run_profile(self.base_candidate(topic_evidence=evidence), topics)["html"]
        proposal = html.split('id="vai-fazer"', 1)[1].split('id="impacto"', 1)[0]
        impact = html.split('id="impacto"', 1)[1].split('id="historico"', 1)[0]
        history = html.split('id="historico"', 1)[1].split('id="dados-eleitorais"', 1)[0]

        self.assertIn("Propõe ampliar atendimento", proposal)
        self.assertIn("<h3>Saúde</h3>", impact)
        self.assertNotIn("Atuação pública documentada", history)

    def test_mixed_evidence_separates_prospective_from_documented_action(self):
        evidence = [
            {
                "topic_id": "saude",
                "evidence_type": "declaração",
                "statement": "Declara intenção de ampliar atendimento",
                "source_publisher": "Canal oficial",
                "published_at": "2026-09-02",
                "source_url": "https://example.test/declaracao",
            },
            {
                "topic_id": "direitos",
                "evidence_type": "atuação",
                "statement": "Atuação anterior documentada",
                "source_publisher": "Câmara",
                "published_at": "2025-05-01",
                "source_url": "https://example.test/atuacao",
            },
        ]
        topics = [
            {"id": "saude", "label": "Saúde", "life_areas": ["SUS"]},
            {"id": "direitos", "label": "Direitos", "life_areas": ["cidadania"]},
        ]
        html = run_profile(self.base_candidate(topic_evidence=evidence), topics)["html"]
        proposal = html.split('id="vai-fazer"', 1)[1].split('id="impacto"', 1)[0]
        impact = html.split('id="impacto"', 1)[1].split('id="historico"', 1)[0]
        history = html.split('id="historico"', 1)[1].split('id="dados-eleitorais"', 1)[0]
        sources = html.split('id="fontes"', 1)[1]

        self.assertIn("Declara intenção de ampliar atendimento", proposal)
        self.assertNotIn("Atuação anterior documentada", proposal)
        self.assertIn("<h3>Saúde</h3>", impact)
        self.assertNotIn("<h3>Direitos</h3>", impact)
        self.assertIn("Atuação anterior documentada", history)
        self.assertIn("https://example.test/declaracao", sources)
        self.assertIn("https://example.test/atuacao", sources)

    def test_multiple_evidence_records_preserve_records_and_dedupe_impact_topic(self):
        evidence = [
            {
                "topic_id": "saude",
                "evidence_type": "proposta",
                "statement": "Primeiro registro",
                "source_publisher": "Fonte A",
                "published_at": "2026-09-01",
                "source_url": "https://example.test/a",
            },
            {
                "topic_id": "saude",
                "evidence_type": "declaração",
                "statement": "Segundo registro",
                "source_publisher": "Fonte B",
                "published_at": "2026-09-02",
                "source_url": "https://example.test/b",
            },
        ]
        topics = [{"id": "saude", "label": "Saúde", "life_areas": ["SUS", "atenção básica"]}]
        html = run_profile(self.base_candidate(topic_evidence=evidence), topics)["html"]
        proposal = html.split('id="vai-fazer"', 1)[1].split('id="impacto"', 1)[0]
        impact = html.split('id="impacto"', 1)[1].split('id="historico"', 1)[0]
        self.assertIn("Primeiro registro", proposal)
        self.assertIn("Segundo registro", proposal)
        self.assertEqual(impact.count("<h3>Saúde</h3>"), 1)

    def test_comparison_helpers_remain_bounded(self):
        output = run_profile(self.base_candidate())
        self.assertEqual(output["normalized"], ["1", "2", "3"])
        self.assertEqual(output["comparison"]["count"], 3)
        self.assertTrue(output["comparison"]["canOpen"])
        self.assertTrue(output["comparison"]["atLimit"])


if __name__ == "__main__":
    unittest.main()

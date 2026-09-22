import json
from pathlib import Path
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_app(expression):
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");
        const storage = new Map();
        const listeners = {{}};
        const classList = {{
          add() {{}},
          remove() {{}},
          contains() {{ return false; }},
          toggle() {{}},
        }};
        const sandbox = {{
          console,
          Date,
          Intl,
          Map,
          Set,
          URL,
          URLSearchParams,
          addEventListener(name, callback) {{ listeners[name] = callback; }},
          dispatchEvent(event) {{ listeners[event.type]?.(event); }},
          history: {{ replaceState() {{}} }},
          location: {{ href: "https://example.test/", search: "" }},
          localStorage: {{
            getItem(key) {{ return storage.has(key) ? storage.get(key) : null; }},
            setItem(key, value) {{ storage.set(key, String(value)); }},
            removeItem(key) {{ storage.delete(key); }},
          }},
          document: {{
            body: {{ dataset: {{ page: "" }}, classList }},
            documentElement: {{ dataset: {{}} }},
            getElementById() {{ return null; }},
            querySelectorAll() {{ return []; }},
            addEventListener() {{}},
          }},
        }};
        sandbox.window = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync("app.js", "utf8"), sandbox);
        const result = vm.runInContext(`{expression}`, sandbox);
        Promise.resolve(result).then(value=>process.stdout.write(JSON.stringify(value)));
        """
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class ComparisonFunnelTests(unittest.TestCase):
    def test_storage_event_and_page_restore_refresh_visible_selection(self):
        result = run_app('(() => {const button={id:"profileCompare",dataset:{candidateId:"101"},classList:{toggle(){}},setAttribute(){}};const status={};document.querySelectorAll=()=>[button];document.getElementById=id=>id==="compareStatus"?status:null;setCompareIds(["101"]);dispatchEvent({type:"storage",key:"qv_compare"});const selected=button.textContent;setCompareIds([]);dispatchEvent({type:"pageshow"});return {selected,cleared:button.textContent,announced:status.textContent.includes("Seleção atualizada")};})()')
        self.assertEqual({"selected":"Remover da comparação","cleared":"Comparar","announced":True}, result)

    def test_url_is_canonical_after_removing_unknown_and_duplicate_ids(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=101,101,invalid,202";location.href="https://example.test/comparar.html"+location.search;let rewritten="";history.replaceState=(_,unused,url)=>{rewritten=url.searchParams.get("ids")};getJSON=async path=>path===DATA.federal?[{tse_id:"101"}]:path===DATA.estadual?[{tse_id:"202"}]:{topics:[]};await initCompare();return rewritten;})()')
        self.assertEqual("101,202", result)

    def test_empty_url_does_not_reuse_previous_selection(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=";setCompareIds(["101","202"]);getJSON=async path=>path===DATA.federal?[{tse_id:"101"}]:path===DATA.estadual?[{tse_id:"202"}]:{topics:[]};await initCompare();return {ids:getCompareIds(),empty:mount.innerHTML.includes("Ninguém selecionado")};})()')
        self.assertEqual({"ids": [], "empty": True}, result)

    def test_partial_snapshot_does_not_erase_selection(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=101,202";setCompareIds(["101","202"]);getJSON=async path=>path===DATA.federal?[{tse_id:"101"}]:path===DATA.estadual?[]:{topics:[]};await initCompare();return {ids:getCompareIds(),error:mount.textContent.includes("Sua seleção foi preservada"),rendered:!!mount.innerHTML};})()')
        self.assertEqual({"ids": ["101", "202"], "error": True, "rendered": False}, result)

    def test_sync_updates_profile_and_list_without_replacing_focused_nodes(self):
        result = run_app('(() => {const make=(id,key)=>({id,dataset:key,attrs:{},classList:{toggle(){}},setAttribute(k,v){this.attrs[k]=v}});const card=make("",{compareId:"101"});const profile=make("profileCompare",{candidateId:"404"});document.querySelectorAll=()=>[card,profile];setCompareIds(["101","202","303"]);syncComparisonControls();const full={card:card.textContent,profile:profile.textContent,disabled:profile.disabled};setCompareIds([]);syncComparisonControls();return {full,empty:{card:card.textContent,profile:profile.textContent,disabled:profile.disabled,pressed:card.attrs["aria-pressed"]}};})()')
        self.assertEqual({"full":{"card":"Remover","profile":"Limite de 3 atingido","disabled":True},"empty":{"card":"Comparar","profile":"Comparar","disabled":False,"pressed":"false"}}, result)

    def test_normalizes_url_selection_to_unique_known_candidates(self):
        result = run_app(
            'typeof normalizeCompareIds === "function" '
            '? normalizeCompareIds(["1", "1", "missing", "2", "3", "4"], ["1", "2", "3"]) '
            ': {"missing": true}'
        )
        self.assertEqual(["1", "2", "3"], result)

    def test_comparison_progress_requires_two_people_and_caps_at_three(self):
        result = run_app(
            'typeof comparisonState === "function" '
            '? [comparisonState(["1"]), comparisonState(["1", "2", "3"])] '
            ': {"missing": true}'
        )
        self.assertEqual(
            [
                {
                    "count": 1,
                    "canOpen": False,
                    "atLimit": False,
                    "message": "Escolha mais 1 pessoa",
                },
                {
                    "count": 3,
                    "canOpen": True,
                    "atLimit": True,
                    "message": "Limite de 3 atingido",
                },
            ],
            result,
        )

    def test_candidate_controls_expose_selection_and_limit_states(self):
        result = run_app(
            '(() => {'
            ' if (typeof candidateCard !== "function") return {"missing": true};'
            ' const selected = candidateCard({tse_id:"1", ballot_name:"Um", party:"P", number:"1"}, "federal", ["1", "2", "3"]);'
            ' const limited = candidateCard({tse_id:"4", ballot_name:"Quatro", party:"P", number:"4"}, "federal", ["1", "2", "3"]);'
            ' return {'
            '   selectedPressed: selected.includes(\'aria-pressed="true"\'),'
            '   selectedRemovable: selected.includes(">Remover</button>"),'
            '   limitedDisabled: limited.includes(" disabled"),'
            '   limitedAriaDisabled: limited.includes(\'aria-disabled="true"\'),'
            '   limitedText: limited.includes(">Limite de 3</button>"),'
            ' };'
            '})()'
        )
        self.assertEqual(
            {
                "selectedPressed": True,
                "selectedRemovable": True,
                "limitedDisabled": True,
                "limitedAriaDisabled": True,
                "limitedText": True,
            },
            result,
        )

    def test_toggle_preserves_canonical_ids_and_limit(self):
        result = run_app('(() => {validCompareIds=["101","202","303","404"];toggleCompare("101");toggleCompare("202");toggleCompare("303");toggleCompare("404");const full=getCompareIds();toggleCompare("202");return [full,getCompareIds()];})()')
        self.assertEqual([["101", "202", "303"], ["101", "303"]], result)

    def test_invalid_and_duplicate_url_ids_are_clean_before_render(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=101,101,invalid,202";getJSON=async path=>path===DATA.federal?[{tse_id:"101",ballot_name:"One"}]:path===DATA.estadual?[{tse_id:"202",ballot_name:"Two"}]:{topics:[]};await initCompare();return {ids:getCompareIds(),columns:(mount.innerHTML.match(/class="compare-person"/g)||[]).length};})()')
        self.assertEqual({"ids": ["101", "202"], "columns": 2}, result)

    def test_invalid_url_clears_invalid_persisted_selection(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=invalid";setCompareIds(["invalid"]);getJSON=async path=>path===DATA.federal?[{tse_id:"101"}]:path===DATA.estadual?[{tse_id:"202"}]:{topics:[]};await initCompare();return {ids:getCompareIds(),empty:mount.innerHTML.includes("Ninguém selecionado")};})()')
        self.assertEqual({"ids": [], "empty": True}, result)

    def test_one_candidate_does_not_render_comparison(self):
        result = run_app('(async () => {const mount={};document.getElementById=id=>id==="compareMount"?mount:null;location.search="?ids=101";getJSON=async path=>path===DATA.federal?[{tse_id:"101"}]:path===DATA.estadual?[{tse_id:"202"}]:{topics:[]};await initCompare();return {ids:getCompareIds(),minimum:mount.innerHTML.includes("Escolha mais 1 pessoa")};})()')
        self.assertEqual({"ids": ["101"], "minimum": True}, result)


if __name__ == "__main__":
    unittest.main()

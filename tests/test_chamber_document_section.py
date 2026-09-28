import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import chamber_document_section as section


class ChamberSectionTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            'source_url': 'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=123',
            'source_origin': {'proposition_id': '123', 'chamber_id': '456', 'author_name': 'Nome Oficial'},
            'institutional_snapshot': {'proposition_id': '123', 'siglaTipo': 'EMR', 'numero': '1',
                'urlInteiroTeor': 'https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=789'},
        }
        self.html = b'<h2 id="areaTituloMenu"><a href="fichadetramitacao?idProposicao=123">EMR 1 CCJC =&gt; PL 816/2007</a></h2><p><strong>Autor</strong><a href="/deputados/456">Nome Oficial</a></p>'
        self.text = 'PROJETO DE LEI Nº 816, DE 2007 Ementa do projeto pai. EMENDA Nº 1 Exclua-se uma expressão do artigo segundo. Deputado Nome Oficial Relator'

    def run_recovery(self, pages=None, item=None):
        def fetch(url):
            return (self.html if 'idProposicao' in url else b'%PDF-fixture'), url, ''
        reader = Mock(is_encrypted=False)
        reader.pages = [Mock(extract_text=Mock(return_value=t)) for t in (pages or [self.text])]
        with patch('pypdf.PdfReader', return_value=reader):
            return section.recover(item or self.item, fetch)

    def test_shared_document_selects_only_exact_parent_and_omits_parent_ementa(self):
        other = self.text.replace('816', '817')
        result = self.run_recovery([other, self.text, other])
        self.assertEqual(result['pages'], [2])
        self.assertTrue(result['text'].startswith('EMENDA'))
        self.assertNotIn('Ementa do projeto pai', result['text'])

    def test_duplicate_parent_section_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ambígua'):
            self.run_recovery([self.text, self.text])

    def test_missing_parent_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ausente'):
            self.run_recovery([self.text.replace('816', '817')])

    def test_wrong_fiche_author_rejected(self):
        self.html = self.html.replace(b'/456', b'/457')
        with self.assertRaisesRegex(RuntimeError, 'autoria'):
            self.run_recovery()

    def test_wrong_pdf_signature_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'encerramento'):
            self.run_recovery([self.text.replace('Nome Oficial', 'Outro Nome')])

    def test_missing_signature_cannot_absorb_next_emenda(self):
        with self.assertRaisesRegex(RuntimeError, 'nova seção'):
            self.run_recovery([self.text.split('Deputado')[0], self.text.replace('816', '817')])

    def test_untrusted_document_host_rejected_before_fetch(self):
        item = copy.deepcopy(self.item)
        item['institutional_snapshot']['urlInteiroTeor'] = 'https://example.com/proposicoesWeb/prop_mostrarintegra?codteor=789'
        with self.assertRaisesRegex(RuntimeError, 'URL oficial'):
            self.run_recovery(item=item)

    def test_substitute_continues_until_explicit_signature(self):
        self.html = self.html.replace(b'EMR 1', b'SBT 1')
        self.item['institutional_snapshot']['siglaTipo'] = 'SBT'
        result = self.run_recovery(['SUBSTITUTIVO AO PROJETO DE LEI Nº 816, DE 2007 Art. 1 Conteúdo.',
                                   'Art. 2 Continuação. Deputado Nome Oficial Relator'])
        self.assertEqual(result['pages'], [1, 2])


if __name__ == '__main__':
    unittest.main()

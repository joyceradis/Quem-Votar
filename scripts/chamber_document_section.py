"""Conservative section extraction for Câmara accessories with empty summaries.

This is staging text, not a replacement ementa or a thematic classification.
The official fiche anchors the accessory to its parent; the PDF must contain
exactly one matching section and an explicit closing rapporteur signature.
"""
import hashlib
import html
import io
import re
from urllib.parse import parse_qs, urlparse


def clean(value):
    return ' '.join(str(value or '').split())


def official_url(url, path, key, value=None):
    parsed = urlparse(url)
    values = parse_qs(parsed.query).get(key, [])
    if (parsed.scheme != 'https' or parsed.netloc != 'www.camara.leg.br'
            or parsed.path != '/proposicoesWeb/' + path
            or len(values) != 1 or not values[0].isdigit()
            or (value is not None and values[0] != str(value))):
        raise RuntimeError('URL oficial da Câmara não corresponde à proposição/documento')
    return values[0]


def recover(item, fetcher, max_pages=80):
    from pypdf import PdfReader
    snapshot = item['institutional_snapshot']
    origin = item['source_origin']
    pid = str(snapshot.get('proposition_id') or '')
    if not pid or pid != str(origin.get('proposition_id')):
        raise RuntimeError('identidade da proposição divergente')
    fiche_url = item['source_url']
    official_url(fiche_url, 'fichadetramitacao', 'idProposicao', pid)
    doc_url = snapshot.get('urlInteiroTeor', '')
    codteor = official_url(doc_url, 'prop_mostrarintegra', 'codteor')
    fiche, final, _ = fetcher(fiche_url)
    official_url(final, 'fichadetramitacao', 'idProposicao', pid)
    markup = fiche.decode('utf-8', errors='strict')
    headings = re.findall(r'<h2 id="areaTituloMenu">(.*?)</h2>', markup, re.S)
    if len(headings) != 1 or not re.search(rf'idProposicao={re.escape(pid)}(?:["&])', headings[0]):
        raise RuntimeError('ficha sem identificação inequívoca')
    title = clean(html.unescape(re.sub('<[^>]+>', '', headings[0])))
    match = re.fullmatch(r'(EMR|SBT) (\d+).*?=> (PLP?) (\d+)/(\d{4})', title)
    if not match:
        raise RuntimeError('tipo de acessório não suportado na recuperação')
    kind, number, parent_kind, parent_number, year = match.groups()
    if kind != snapshot.get('siglaTipo') or number != str(snapshot.get('numero')):
        raise RuntimeError('tipo/número da ficha diverge do snapshot')
    authors = re.findall(r'<strong>Autor</strong>(.*?)</p>', markup, re.S)
    author_id = str(origin.get('chamber_id') or '')
    author = clean(origin.get('author_name'))
    if (len(authors) != 1 or not author_id.isdigit() or not author
            or f'/deputados/{author_id}"' not in authors[0]):
        raise RuntimeError('autoria da ficha não corresponde ao vínculo oficial')
    raw, final, _ = fetcher(doc_url)
    official_url(final, 'prop_mostrarintegra', 'codteor', codteor)
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 0 < len(reader.pages) <= max_pages:
        raise RuntimeError('PDF criptografado ou fora do limite de páginas')
    pages = [page.extract_text() or '' for page in reader.pages]
    if sum(map(len, pages)) > 500_000:
        raise RuntimeError('PDF excede limite de texto extraído')
    number_pattern = re.escape(f'{int(parent_number):,}'.replace(',', '.'))
    parent = r'PROJETOS? DE LEI' + (' COMPLEMENTAR' if parent_kind == 'PLP' else '')
    parent += rf' Nº {number_pattern}(?:, DE {year}|/{year[-2:]})\b'
    starts = []
    for index, page in enumerate(pages):
        text = clean(page)
        heading = re.search(parent, text[:450])
        marker = re.search(r'EMENDA\s+N[ºo°]', text[:1500]) if kind == 'EMR' else re.search(r'SUBSTITUTIVO A[OÓ]', text[:450])
        if heading and marker and (kind == 'EMR' or marker.start() < heading.start()):
            starts.append(index)
    if len(starts) != 1:
        raise RuntimeError('seção do acessório ausente ou ambígua no PDF')
    start = starts[0]
    blocks = []
    section_number = None
    section_marker = re.compile(r'EMENDA\s+N[ºo°]|SUBSTITUTIVO A[OÓ]')
    ending = re.compile(r'Deputado\s+' + re.escape(author) + r'\s+Relator\b', re.I)
    for end in range(start, len(pages)):
        text = clean(pages[end])
        body_start = 0
        if end == start:
            marker = re.search(r'EMENDA\s+N[ºo°]' if kind == 'EMR' else r'SUBSTITUTIVO A[OÓ]', text)
            text = text[marker.start():]
            body_start = marker.end() - marker.start()
            if kind == 'EMR':
                explicit_number = re.match(r'\s*(\d+)\b', text[body_start:])
                if explicit_number:
                    section_number = explicit_number.group(1)
                    if int(section_number) != int(number):
                        raise RuntimeError('número da emenda no PDF diverge da ficha')
        signature = ending.search(text)
        # A page is not a section boundary. Never borrow another accessory's
        # signature, including a later heading on this same physical page.
        next_section = section_marker.search(text, body_start)
        if next_section and (signature is None or next_section.start() < signature.end()):
            raise RuntimeError('nova seção antes da assinatura do acessório')
        if next_section and section_number is None:
            raise RuntimeError('seção sem número ambígua na mesma página')
        blocks.append(text[:signature.end()] if signature else text)
        if signature:
            break
    else:
        raise RuntimeError('seção sem encerramento e autoria verificáveis')
    excerpt = '\n'.join(blocks)
    if len(excerpt) < 40:
        raise RuntimeError('seção documental insuficiente')
    return dict(text=excerpt, title=title, document_url=doc_url,
                document_sha256=hashlib.sha256(raw).hexdigest(),
                fiche_sha256=hashlib.sha256(fiche).hexdigest(),
                pages=list(range(start + 1, end + 2)), page_count=len(pages),
                section_number=section_number,
                section_identity_basis=('fiche_parent_number_and_signature' if section_number
                                        else 'fiche_unique_parent_and_signature'),
                parent_context_only=f'{parent_kind} {parent_number}/{year}')

#!/usr/bin/env python3
"""Rote Liste der Farn- und Blütenpflanzen Österreichs (Stapfia 114, 2022) aus der Excel-Tabelle lesen.
  python rl_parse.py tabelle.xlsx -> scripts/rl_source.json
Übernimmt nur die Einstufungen (Kategorie, Naturräume, Bundesländer, Verantwortlichkeit, Areal, Lebensdauer)
und den deutschen Namen, keine Anmerkungstexte. Braucht openpyxl (nur lokal, nicht in der Action)."""
import json, os, re, sys
import openpyxl

CATS = {'LC', 'VU', 'n', 'EN', 'NT', 'CR', 'G', 'DD', 'RE', 'RE?', '?', 'RE,n'}
LATIN = re.compile(r'^[A-Z][a-z-]+ (×|x |[a-z"(-]|Sect)')
clean = lambda v: re.sub(r'\s+', ' ', str(v)).strip() if v is not None else ''

def main(path):
    ws = openpyxl.load_workbook(path, read_only=True)['TBL_RL_FINALDRUCK']
    rows = [[clean(x) for x in r] + [''] * 24 for r in ws.iter_rows(values_only=True)]
    head = rows[1][:23]
    assert head[:6] == ['Taxon', 'RL', 'A', 'B', 'R', 'AL'] and head[19] == 'B', head
    out, syn = [], []
    for i in range(2, len(rows)):
        r = rows[i]
        if '→' in r[0] and not any(r[1:22]):
            old, new = [x.strip() for x in r[0].split('→', 1)]
            m = re.match(r'^([A-Z])\. (.+)$', new)
            if m and old.split()[0].startswith(m.group(1)): new = old.split()[0] + ' ' + m.group(2)
            syn.append([old, new]); continue
        has = r[1] in CATS or any(r[2:21])
        if not has or not LATIN.match(r[0]): continue
        # Folgezeilen bis zum nächsten Taxon: Synonyme („Syn. …“), Aggregat in Klammern, deutscher Name
        de, syns, genus = '', [], r[0].split()[0]
        for nxt in rows[i + 1:i + 5]:
            if nxt[1] in CATS or any(nxt[2:21]) or LATIN.match(nxt[0]) or '→' in nxt[0] or not nxt[0]: break
            if nxt[0].startswith('Syn.'):
                for x in nxt[0][4:].split(','):
                    x = re.sub(r'^([A-Z])\. ', lambda m: genus + ' ' if genus.startswith(m.group(1)) else m.group(0), x.strip())
                    if re.match(r'^[A-Z][a-z-]+ [a-z]', x): syns.append(x)
            elif not nxt[0].startswith(('(', '=')) and not de: de = nxt[0]
        out.append([r[0], de, r[1], r[5:10], r[10:20], r[20], r[21], r[22], syns])
    meta = {'quelle': 'Schratt-Ehrendorfer, L., Niklfeld, H., Schröck, C. & Stöhr, O. (Hrsg.) 2022: Rote Liste der Farn- und Blütenpflanzen Österreichs. Stapfia 114',
            'nat': head[5:10], 'bl': head[10:20]}
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rl_source.json')
    json.dump({**meta, 's': out, 'syn': syn}, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(out)} Taxa, {len(syn)} Verweise -> {dst}')

if __name__ == '__main__':
    main(sys.argv[1])

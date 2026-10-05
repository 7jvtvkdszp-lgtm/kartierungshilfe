#!/usr/bin/env python3
"""Rote Liste Österreich für die Kartierungshilfe: rl.json aus scripts/rl_source.json.
  - Namen der Roten Liste auf iNaturalist-Namen abbilden (iNat findet auch Synonyme; Cache scripts/rl_names.json)
  - Unterarten ohne eigene Artzeile zur Art zusammenfassen (stärkste Gefährdung, bestes Vorkommen je Bundesland)
  - je Quadrant Österreichs die Bundesländer (V, nT, oT, S, K, St, O, N, W, B) aus den iNat-Ortsgrenzen
Läuft als GitHub Action, braucht nur die Python-Standardbibliothek."""
import json, os, re, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_atlas import inat, in_ring, cells, bounds, quad_id, INAT_TRACHEOPHYTA, PLACE_AT, sp_name

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, CACHE = os.path.join(HERE, 'rl_source.json'), os.path.join(HERE, 'rl_names.json')
ORDER = ['RE', 'RE?', 'CR', 'EN', 'VU', 'G', 'NT', 'DD', 'LC', 'n', '?', '']  # stärkste Gefährdung zuerst
PRES = ['●', '●*', 'e', 'le', 'e?', 'le?', 'u', 'u?', '?', '†,u', '†', '†?', '†*', '–', '']  # bestes Vorkommen zuerst
STATES = [('V', 'Vorarlberg'), ('T', 'Tirol'), ('S', 'Salzburg'), ('K', 'Kärnten'), ('St', 'Steiermark'),
          ('O', 'Oberösterreich'), ('N', 'Niederösterreich'), ('W', 'Wien'), ('B', 'Burgenland')]

def key(name):
    n = re.sub(r'\s+(s\.\s?lat\.|s\.\s?str\.|s\.\s?orig\.|auct\.|ined\.|agg\.|subagg\.)', '', name).replace(' x ', ' × ')
    p = n.split()
    return ' '.join(p[:3]) if len(p) > 2 and p[1] == '×' else ' '.join(p[:2])

def worst(vals): return min(vals, key=lambda v: ORDER.index(v) if v in ORDER else len(ORDER))
def best(vals): return min(vals, key=lambda v: PRES.index(v) if v in PRES else 8)

def species_rows(src):
    groups = {}
    for r in src['s']:
        if 'Sect' in r[0]: continue
        groups.setdefault(key(r[0]), []).append(r)
    out = {}
    for k, rs in groups.items():
        exact = [r for r in rs if key(r[0]) == re.sub(r'\s+(s\.\s?lat\.|s\.\s?str\.|s\.\s?orig\.|agg\.)$', '', r[0]).replace(' x ', ' × ')]
        if exact:
            r = exact[0]; out[k] = [r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], 0, [key(x) for x in r[8]]]
        else:  # nur Unterarten oder Varietäten
            cats = [r[2] for r in rs if r[2]]
            out[k] = [k, '', worst(cats) if cats else '',
                      [worst([r[3][i] for r in rs if r[3][i] in ORDER] or [best([r[3][i] for r in rs])]) for i in range(5)],
                      [best([r[4][i] for r in rs]) for i in range(10)], next((r[5] for r in rs if r[5]), ''), next((r[6] for r in rs if r[6]), ''), rs[0][7], 1, []]
    return out

def inat_species(name, cache):
    if name in cache: return cache[name]
    j = inat('taxa', {'q': name, 'taxon_id': INAT_TRACHEOPHYTA, 'per_page': 10})
    res = None
    for t in (j or {}).get('results', []):
        if t.get('rank_level', 99) > 10: continue
        if name in (t['name'], t.get('matched_term', '')) or sp_name(t['name'], t['rank_level']) == name:
            res = sp_name(t['name'], t['rank_level']); break
    cache[name] = res
    return res

def place_polys(q, level):
    j = inat('places/autocomplete', {'q': q, 'per_page': 20})
    for p in (j or {}).get('results', []):
        if p.get('admin_level') == level and PLACE_AT in (p.get('ancestor_place_ids') or []) and p['name'].startswith(q[:5]):
            g = (inat(f"places/{p['id']}") or {}).get('results', [{}])[0].get('geometry_geojson')
            if g:
                polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
                # vereinfachen: für Quadranten von etwa 6 km reichen 1500 Punkte je Ring
                polys = [[ring[::max(1, len(ring) // 1500)] for ring in poly] for poly in polys]
                xs = [pt[0] for poly in polys for pt in poly[0]]; ys = [pt[1] for poly in polys for pt in poly[0]]
                print(f'  {q}: Ort {p["id"]} ({p["name"]}), {sum(len(poly[0]) for poly in polys)} Punkte', file=sys.stderr)
                return polys, (min(xs), min(ys), max(xs), max(ys))
    print(f'  {q}: keine Grenze gefunden', file=sys.stderr)
    return None

def inside(x, y, pb):
    polys, (x0, y0, x1, y1) = pb
    if not (x0 <= x <= x1 and y0 <= y <= y1): return False
    return any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in polys)

def quad_states():
    shapes = {c: place_polys(n, 10) for c, n in STATES}
    lienz = place_polys('Lienz', 20)  # Osttirol = Bezirk Lienz
    shapes = {c: s for c, s in shapes.items() if s}
    if len(shapes) < 9: print(f'Nur {len(shapes)} von 9 Bundesländern gefunden', file=sys.stderr)
    cl, _ = cells()
    out = {}
    for r2, c2 in cl:
        s, n, w, e = bounds(r2, c2)
        found = []
        for i in range(5):
            for k in range(5):
                x, y = w + (e - w) * (0.02 + 0.96 * i / 4), s + (n - s) * (0.02 + 0.96 * k / 4)
                for c, pb in shapes.items():
                    if inside(x, y, pb):
                        if c == 'T': c = 'oT' if lienz and inside(x, y, lienz) else 'nT'
                        if c not in found: found.append(c)
                        break
        if found: out[quad_id(r2, c2)] = ','.join(found)
    print(f'{len(out)} Quadranten mit Bundesland', file=sys.stderr)
    return out

def main():
    src = json.load(open(SRC))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    sp = species_rows(src)
    syn_new = {}  # neuer RL-Name -> alte Namen (falls iNat noch den alten führt)
    for old, new in src['syn']:
        if ' ' in old and ' ' in new: syn_new.setdefault(key(new), []).append(key(old))
    rows, miss = {}, []
    for n, (k, r) in enumerate(sp.items()):
        name = inat_species(k, cache)
        for o in r[9] + syn_new.get(k, []):  # Synonyme, falls iNat einen anderen Namen führt
            if name: break
            if o != k: name = inat_species(o, cache)
        if not name: miss.append(k); continue
        prev = rows.get(name)
        if prev and ORDER.index(prev[3]) <= ORDER.index(r[2] if r[2] in ORDER else ''): continue  # zwei RL-Taxa auf eine iNat-Art: stärkere Gefährdung gewinnt
        rows[name] = [name, r[0], r[1], r[2], '|'.join(r[3]), '|'.join(r[4]), r[5], r[6], r[7], r[8]]
        if n % 200 == 0:
            print(f'Namen {n + 1}/{len(sp)}', file=sys.stderr)
            json.dump(cache, open(CACHE, 'w'), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(cache, open(CACHE, 'w'), ensure_ascii=False, indent=0, sort_keys=True)
    print(f'{len(rows)} Arten zugeordnet, {len(miss)} ohne iNat-Treffer: {", ".join(miss[:40])}', file=sys.stderr)
    out = {'v': 1, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'quelle': src['quelle'],
           'nat': src['nat'], 'bl': src['bl'], 'q': quad_states(), 's': sorted(rows.values()), 'miss': miss}
    json.dump(out, open('rl.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'rl.json: {len(rows)} Arten, {len(out["q"])} Quadranten', file=sys.stderr)

if __name__ == '__main__':
    main()

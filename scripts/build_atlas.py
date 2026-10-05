#!/usr/bin/env python3
"""Österreich-Atlas für die Kartierungshilfe: je Quadrant die Pflanzenarten (ohne Moose).
  python build_atlas.py inat   -> part_inat.json  (iNaturalist, alle Jahre)
  python build_atlas.py gbif   -> part_gbif.json  (GBIF, Gefäßpflanzen der letzten 20 Jahre, Namen auf iNat abgeglichen)
  python build_atlas.py merge  -> atlas.json      (Vereinigung: Art kommt im Quadranten vor, wenn eine Quelle sie meldet)
Läuft monatlich als GitHub Action, braucht nur die Python-Standardbibliothek."""
import json, math, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

INAT = 'https://api.inaturalist.org/v1'
GBIF = 'https://api.gbif.org/v1'
PLACE_AT = 8057
MOSS_IDS = '311249,64615,56327'
GBIF_TRACHEOPHYTA = 7707728  # Gefäßpflanzen, damit ohne Moose
YEARS = 20
LAT0, LON0 = 56.0, 5 + 40 / 60
UA = 'Kartierungshilfe-Atlas/1.0 (github.com/7jvtvkdszp-lgtm/kartierungshilfe)'
S, N, W, E = 46.35, 49.05, 9.5, 17.2  # Österreich grob
NAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gbif_names.json')

last = {}
def get(base, path, params, gap):
    url = f'{base}/{path}' + ('?' + urllib.parse.urlencode(params) if params else '')
    for attempt in range(6):
        wait = gap - (time.time() - last.get(base, 0))
        if wait > 0: time.sleep(wait)
        last[base] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            print(f'  HTTP {e.code}, neuer Versuch: {url}', file=sys.stderr)
        except Exception as e:
            print(f'  Fehler ({e}), neuer Versuch', file=sys.stderr)
        time.sleep(5 * 2 ** attempt)
    raise RuntimeError('nicht erreichbar: ' + url)
inat = lambda path, params=None: get(INAT, path, params, 1.05)
gbif = lambda path, params=None: get(GBIF, path, params, 0.25)

def quad_id(r2, c2):
    r, c = r2 // 2, c2 // 2
    return f'{r:02d}{c:02d}/{1 + (r2 % 2) * 2 + (c2 % 2)}'

def bounds(r2, c2):
    n = LAT0 - r2 / 20
    w = LON0 + c2 / 12
    return n - 0.05, n, w, w + 1 / 12

def load_polys():
    try:
        j = inat(f'places/{PLACE_AT}')
        g = j['results'][0].get('geometry_geojson')
        if not g: return None
        return g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    except Exception as e:
        print('Keine Grenzgeometrie:', e, file=sys.stderr)
        return None

def in_ring(x, y, ring):
    inside = False
    for i in range(len(ring)):
        x1, y1 = ring[i - 1][:2]; x2, y2 = ring[i][:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside

def in_polys(x, y, polys):
    return any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in polys)

def cells():
    """Quadranten, die Österreich berühren (25 Stichpunkte je Quadrant). Ohne Grenze: alle im Rechteck."""
    polys = load_polys()
    out = []
    for r2 in range(math.floor((LAT0 - N) * 20), math.floor((LAT0 - S) * 20) + 1):
        for c2 in range(math.floor((W - LON0) * 12), math.floor((E - LON0) * 12) + 1):
            s, n, w, e = bounds(r2, c2)
            if polys is not None:
                pts = [(w + (e - w) * i / 4, s + (n - s) * k / 4) for i in range(5) for k in range(5)]
                if not any(in_polys(x, y, polys) for x, y in pts): continue
            out.append((r2, c2))
    print(f'{len(out)} Quadranten (Grenze {"ja" if polys else "nein"})', file=sys.stderr)
    return out, polys is not None

def sp_name(name, rank):
    return name if rank == 10 else ' '.join(name.split()[:2])

def run_inat():
    cl, border = cells()
    data, common = {}, {}
    for k, (r2, c2) in enumerate(cl):
        s, n, w, e = bounds(r2, c2)
        found, page = {}, 1
        while True:
            j = inat('observations/species_counts', {'place_id': PLACE_AT, 'swlat': s, 'swlng': w, 'nelat': n, 'nelng': e,
                     'verifiable': 'true', 'iconic_taxa': 'Plantae', 'without_taxon_id': MOSS_IDS,
                     'per_page': 500, 'page': page, 'locale': 'de'})
            for res in j['results']:
                t = res.get('taxon') or {}
                if not t or t.get('rank_level', 99) > 10: continue
                name = sp_name(t['name'], t['rank_level'])
                found[name] = found.get(name, 0) + res['count']
                if t['rank_level'] == 10 and t.get('preferred_common_name'): common[name] = t['preferred_common_name']
            if page * 500 >= j['total_results']: break
            page += 1
        data[quad_id(r2, c2)] = found
        if k % 100 == 0: print(f'iNat {k + 1}/{len(cl)}', file=sys.stderr)
    return {'border': border, 'q': [quad_id(r2, c2) for r2, c2 in cl], 'd': data, 'c': common}

def inat_name(canonical, names_cache_misc):
    """GBIF-Name auf den iNaturalist-Namen abbilden (iNat findet auch Synonyme)."""
    j = inat('taxa', {'q': canonical, 'iconic_taxa': 'Plantae', 'per_page': 10, 'locale': 'de'})
    for t in (j or {}).get('results', []):
        if t.get('rank_level', 99) > 10: continue
        terms = {t['name'], t.get('matched_term', '')}
        if canonical in terms or sp_name(t['name'], t['rank_level']) == canonical:
            return sp_name(t['name'], t['rank_level']), (t.get('preferred_common_name') or '') if t['rank_level'] == 10 else ''
    return canonical, ''

def run_gbif():
    cl, border = cells()
    y1 = datetime.now(timezone.utc).year; y0 = y1 - YEARS
    names = json.load(open(NAMES, encoding='utf-8')) if os.path.exists(NAMES) else {}
    raw = {}
    for k, (r2, c2) in enumerate(cl):
        s, n, w, e = bounds(r2, c2)
        j = gbif('occurrence/search', {'country': 'AT', 'taxonKey': GBIF_TRACHEOPHYTA, 'year': f'{y0},{y1}',
                 'hasCoordinate': 'true', 'hasGeospatialIssue': 'false', 'occurrenceStatus': 'PRESENT',
                 'decimalLatitude': f'{s:.5f},{n:.5f}', 'decimalLongitude': f'{w:.5f},{e:.5f}',
                 'facet': 'speciesKey', 'facetLimit': 3000, 'limit': 0})
        counts = {}
        for f in (j or {}).get('facets', []):
            for c in f['counts']: counts[c['name']] = c['count']
        raw[quad_id(r2, c2)] = counts
        if k % 100 == 0: print(f'GBIF {k + 1}/{len(cl)}: {len(counts)} Arten', file=sys.stderr)
    keys = {key for c in raw.values() for key in c}
    todo = [key for key in keys if key not in names]
    print(f'{len(keys)} GBIF-Arten, {len(todo)} Namen neu abzugleichen', file=sys.stderr)
    for i, key in enumerate(todo):
        sp = gbif(f'species/{key}')
        canonical = (sp or {}).get('canonicalName') or (sp or {}).get('species') or ''
        if not canonical: names[key] = ['', '']; continue
        try: names[key] = list(inat_name(canonical, None))
        except Exception: names[key] = [canonical, '']
        if i % 200 == 0:
            print(f'Namen {i + 1}/{len(todo)}', file=sys.stderr)
            json.dump(names, open(NAMES, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(names, open(NAMES, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    data, common = {}, {}
    for qid, counts in raw.items():
        found = {}
        for key, cnt in counts.items():
            name, cn = names.get(key, ['', ''])
            if not name: continue
            found[name] = found.get(name, 0) + cnt
            if cn: common[name] = cn
        data[qid] = found
    return {'border': border, 'years': [y0, y1], 'q': [quad_id(r2, c2) for r2, c2 in cl], 'd': data, 'c': common}

def merge():
    parts = {}
    for src in ('inat', 'gbif'):
        try: parts[src] = json.load(open(f'part_{src}.json', encoding='utf-8'))
        except Exception as e: print(f'{src} fehlt: {e}', file=sys.stderr)
    if 'inat' not in parts: raise SystemExit('iNat-Teil fehlt')
    q = parts['inat']['q']; qi = {x: i for i, x in enumerate(q)}
    species, common = {}, {}
    for src, p in parts.items():
        common.update({k: v for k, v in p['c'].items() if k not in common or src == 'inat'})
        for qid, found in p['d'].items():
            if qid not in qi: continue
            for name, cnt in found.items():
                d = species.setdefault(name, {})
                # pro Quelle eigene Zahl; GBIF enthält bestätigte iNat-Funde, darum Höchstwert statt Summe
                d[qi[qid]] = max(d.get(qi[qid], 0), cnt)
    if not parts['inat']['border']:  # ohne Grenze: nur Quadranten mit Funden
        used = sorted({i for d in species.values() for i in d})
        remap = {o: n for n, o in enumerate(used)}
        q = [q[i] for i in used]
        species = {s: {remap[i]: c for i, c in d.items()} for s, d in species.items()}
    out = {'v': 2, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'src': ['iNaturalist'] + ([f'GBIF {parts["gbif"]["years"][0]}–{parts["gbif"]["years"][1]}'] if 'gbif' in parts else []),
           'n': len(q), 'q': q,
           's': [[name, common.get(name, ''), [x for i in sorted(d) for x in (i, d[i])]] for name, d in sorted(species.items())]}
    json.dump(out, open('atlas.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'atlas.json: {len(q)} Quadranten, {len(species)} Arten, Quellen {out["src"]}', file=sys.stderr)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'inat'
    if mode == 'merge': merge()
    else:
        res = run_inat() if mode == 'inat' else run_gbif()
        json.dump(res, open(f'part_{mode}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

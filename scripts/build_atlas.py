#!/usr/bin/env python3
"""Österreich-Atlas für die Kartierungshilfe: je Quadrant die Pflanzenarten (ohne Moose).
  python build_atlas.py inat   -> part_inat.json  (iNaturalist, alle Jahre)
  python build_atlas.py gbif   -> part_gbif.json  (GBIF, Gefäßpflanzen der letzten 20 Jahre, Namen auf iNat abgeglichen)
  python build_atlas.py rg     -> scripts/inat_rg.json (Arten mit iNat-Funden in Österreich, gesamt und mit Forschungsqualität)
  python build_atlas.py merge  -> atlas.json      (Vereinigung: Art kommt im Quadranten vor, wenn eine Quelle sie meldet)
  python build_atlas.py rgfilter -> atlas.json    (nur den Einzelmeldungs-Filter auf ein vorhandenes atlas.json anwenden)
Einzelmeldungen: eine Art mit nur einer Meldung in ganz Österreich, die nur von iNaturalist kommt und dort keine
Forschungsqualität hat, wird weggelassen (Wunsch von Thomas).
Läuft monatlich als GitHub Action, braucht nur die Python-Standardbibliothek."""
import json, math, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

INAT = 'https://api.inaturalist.org/v1'
GBIF = 'https://api.gbif.org/v1'
PLACE_AT = 8057
INAT_TRACHEOPHYTA = 211194  # Gefäßpflanzen: ohne Moose, Algen (z. B. Chara, Trentepohlia)
GBIF_TRACHEOPHYTA = 7707728  # Gefäßpflanzen, damit ohne Moose
YEARS = 20
LAT0, LON0 = 56.0, 5 + 40 / 60
UA = 'Kartierungshilfe-Atlas/1.0 (github.com/7jvtvkdszp-lgtm/kartierungshilfe)'
S, N, W, E = 46.35, 49.05, 9.5, 17.2  # Österreich grob
NAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gbif_names.json')
RG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inat_rg.json')

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
                     'verifiable': 'true', 'taxon_id': INAT_TRACHEOPHYTA,
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

def name_key(n):
    return re.sub(r'×|-|\s+x\s+|\s+', '', n.lower())

def junk_name(n):
    """Gattungsangaben (\"Alchemilla spec\") und Hybridformeln (\"A b x c\") sind keine Arten."""
    return bool(re.search(r'\s(spec|sp|spp)\.?$', n, re.I) or re.match(r'^\S+ \S+ x \S+', n))

def inat_name(canonical, names_cache_misc):
    """GBIF-Name auf den iNaturalist-Namen abbilden (iNat findet auch Synonyme)."""
    # exakter Name vor Synonym-Treffer, Schreibvarianten (bella-donna/belladonna, fehlendes ×) gelten als gleich
    for path in ('taxa', 'taxa/autocomplete'):
        j = inat(path, {'q': canonical, 'taxon_id': INAT_TRACHEOPHYTA, 'per_page': 30, 'locale': 'de'})
        ts = [t for t in (j or {}).get('results', []) if t.get('rank_level', 99) <= 10]
        hit = next((t for t in ts if canonical in (t['name'], sp_name(t['name'], t['rank_level'])) or name_key(t['name']) == name_key(canonical)), None) \
            or next((t for t in ts if name_key(t.get('matched_term') or '') == name_key(canonical)), None)
        if hit: return sp_name(hit['name'], hit['rank_level']), (hit.get('preferred_common_name') or '') if hit['rank_level'] == 10 else ''
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

def run_rg():
    out = {}
    for key, extra in (('all', {'verifiable': 'true'}), ('rg', {'quality_grade': 'research'})):
        found, page = {}, 1
        while True:
            j = inat('observations/species_counts', {'place_id': PLACE_AT, 'taxon_id': INAT_TRACHEOPHYTA, 'per_page': 500, 'page': page, **extra})
            for res in j['results']:
                t = res.get('taxon') or {}
                if not t or t.get('rank_level', 99) > 10: continue
                n = sp_name(t['name'], t['rank_level']); found[n] = found.get(n, 0) + res['count']
            if page * 500 >= j['total_results']: break
            page += 1
        out[key] = found
        print(f'iNat Österreich {key}: {len(found)} Arten', file=sys.stderr)
    json.dump(out, open(RG, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)

def drop_single(species, other=None):
    """Einzelmeldungen ohne Forschungsqualität entfernen. species: Name -> {Quadrant: Anzahl};
    other: Namen, die auch eine andere Quelle (GBIF) meldet – die bleiben. Gibt die entfernten Namen zurück."""
    try: rg = json.load(open(RG, encoding='utf-8'))
    except Exception as e: print(f'inat_rg.json fehlt, kein Einzelmeldungs-Filter: {e}', file=sys.stderr); return []
    gone = [n for n, d in species.items() if sum(d.values()) == 1 and rg['all'].get(n, 0) == 1 and n not in rg['rg'] and not (other and n in other)]
    for n in gone: del species[n]
    print(f'{len(gone)} Einzelmeldungen ohne Forschungsqualität entfernt', file=sys.stderr)
    return sorted(gone)

def rg_filter():
    a = json.load(open('atlas.json', encoding='utf-8'))
    species = {n: {occ[i]: occ[i + 1] for i in range(0, len(occ), 2)} for n, c, occ in a['s']}
    gone = set(drop_single(species))
    a['s'] = [r for r in a['s'] if r[0] not in gone]; a['drop'] = sorted(gone)
    json.dump(a, open('atlas.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

def merge():
    parts = {}
    for src in ('inat', 'gbif'):
        try: parts[src] = json.load(open(f'part_{src}.json', encoding='utf-8'))
        except Exception as e: print(f'{src} fehlt: {e}', file=sys.stderr)
    if 'inat' not in parts: raise SystemExit('iNat-Teil fehlt')
    q = parts['inat']['q']; qi = {x: i for i, x in enumerate(q)}
    species, common = {}, {}
    # GBIF-Namen, die iNat nur anders schreibt, auf den iNat-Namen legen
    inat_names = {n for found in parts['inat']['d'].values() for n in found}
    by_key = {name_key(n): n for n in inat_names}
    if 'gbif' in parts:
        p = parts['gbif']
        fix = lambda n: n if n in inat_names else by_key.get(name_key(n), n)
        def fixed(found):
            out = {}
            for n, c in found.items():
                if not junk_name(n): out[fix(n)] = max(out.get(fix(n), 0), c)
            return out
        p['d'] = {qid: fixed(found) for qid, found in p['d'].items()}
        p['c'] = {fix(n): c for n, c in p['c'].items()}
    for src, p in parts.items():
        common.update({k: v for k, v in p['c'].items() if k not in common or src == 'inat'})
        for qid, found in p['d'].items():
            if qid not in qi: continue
            for name, cnt in found.items():
                d = species.setdefault(name, {})
                # pro Quelle eigene Zahl; GBIF enthält bestätigte iNat-Funde, darum Höchstwert statt Summe
                d[qi[qid]] = max(d.get(qi[qid], 0), cnt)
    gbif_seen = {n for found in parts['gbif']['d'].values() for n in found} if 'gbif' in parts else set()
    gone = drop_single(species, gbif_seen)
    if not parts['inat']['border']:  # ohne Grenze: nur Quadranten mit Funden
        used = sorted({i for d in species.values() for i in d})
        remap = {o: n for n, o in enumerate(used)}
        q = [q[i] for i in used]
        species = {s: {remap[i]: c for i, c in d.items()} for s, d in species.items()}
    out = {'v': 2, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'src': ['iNaturalist'] + ([f'GBIF {parts["gbif"]["years"][0]}–{parts["gbif"]["years"][1]}'] if 'gbif' in parts else []),
           'n': len(q), 'q': q,
           's': [[name, common.get(name, ''), [x for i in sorted(d) for x in (i, d[i])]] for name, d in sorted(species.items())],
           'drop': gone}
    json.dump(out, open('atlas.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'atlas.json: {len(q)} Quadranten, {len(species)} Arten, Quellen {out["src"]}', file=sys.stderr)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'inat'
    if mode == 'merge': merge()
    elif mode == 'rg': run_rg()
    elif mode == 'rgfilter': rg_filter()
    else:
        res = run_inat() if mode == 'inat' else run_gbif()
        json.dump(res, open(f'part_{mode}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

#!/usr/bin/env python3
"""Sammelt für jeden Quadranten Österreichs die Pflanzenarten (ohne Moose) aus iNaturalist
und schreibt atlas.json für die Kartierungshilfe: Häufigkeitsklassen und Verbreitungskarten.
Läuft monatlich als GitHub Action, braucht nur die Python-Standardbibliothek."""
import json, math, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = 'https://api.inaturalist.org/v1'
PLACE_AT = 8057
MOSS_IDS = '311249,64615,56327'
LAT0, LON0 = 56.0, 5 + 40 / 60
UA = 'Kartierungshilfe-Atlas/1.0 (github.com/7jvtvkdszp-lgtm/kartierungshilfe)'
# Österreich grob: 46.37–49.02 N, 9.53–17.17 O
S, N, W, E = 46.35, 49.05, 9.5, 17.2

last = 0.0
def get(path, params):
    global last
    url = f'{API}/{path}?' + urllib.parse.urlencode(params)
    for attempt in range(6):
        wait = 1.05 - (time.time() - last)
        if wait > 0: time.sleep(wait)
        last = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print(f'  Fehler ({e}), neuer Versuch', file=sys.stderr)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError('iNaturalist nicht erreichbar: ' + url)

def quad_id(r2, c2):
    r, c = r2 // 2, c2 // 2
    return f'{r:02d}{c:02d}/{1 + (r2 % 2) * 2 + (c2 % 2)}'

def bounds(r2, c2):
    n = LAT0 - r2 / 20
    w = LON0 + c2 / 12
    return n - 0.05, n, w, w + 1 / 12

# Grenze Österreichs für die Liste der Quadranten (Punkt-im-Polygon an 25 Stichpunkten je Quadrant)
def load_polys():
    try:
        j = get(f'places/{PLACE_AT}', {})
        g = j['results'][0].get('geometry_geojson')
        if not g: return None
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        return [[ring for ring in p] for p in polys]
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
    for p in polys:
        if in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]):
            return True
    return False

def main():
    polys = load_polys()
    r2a, r2b = math.floor((LAT0 - N) * 20), math.floor((LAT0 - S) * 20)
    c2a, c2b = math.floor((W - LON0) * 12), math.floor((E - LON0) * 12)
    cells = []
    for r2 in range(r2a, r2b + 1):
        for c2 in range(c2a, c2b + 1):
            s, n, w, e = bounds(r2, c2)
            if polys is not None:
                pts = [(w + (e - w) * i / 4, s + (n - s) * k / 4) for i in range(5) for k in range(5)]
                if not any(in_polys(x, y, polys) for x, y in pts): continue
            cells.append((r2, c2))
    print(f'{len(cells)} Quadranten zu laden (Grenze {"ja" if polys else "nein"})', file=sys.stderr)
    quads, species, common = [], {}, {}
    for k, (r2, c2) in enumerate(cells):
        s, n, w, e = bounds(r2, c2)
        qid = quad_id(r2, c2)
        found = {}
        page = 1
        while True:
            j = get('observations/species_counts', {'place_id': PLACE_AT, 'swlat': s, 'swlng': w, 'nelat': n, 'nelng': e,
                    'verifiable': 'true', 'iconic_taxa': 'Plantae', 'without_taxon_id': MOSS_IDS,
                    'per_page': 500, 'page': page, 'locale': 'de'})
            for res in j['results']:
                t = res.get('taxon') or {}
                if not t or t.get('rank_level', 99) > 10: continue
                name = t['name'] if t['rank_level'] == 10 else ' '.join(t['name'].split()[:2])
                found[name] = found.get(name, 0) + res['count']
                if t['rank_level'] == 10 and t.get('preferred_common_name'): common[name] = t['preferred_common_name']
            if page * 500 >= j['total_results']: break
            page += 1
        if polys is None and not found: continue  # ohne Grenze: nur Quadranten mit Funden zählen
        qi = len(quads); quads.append(qid)
        for name, cnt in found.items(): species.setdefault(name, []).extend([qi, cnt])
        if k % 50 == 0: print(f'{k + 1}/{len(cells)} {qid}: {len(found)} Arten, gesamt {len(species)}', file=sys.stderr)
    out = {'v': 1, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'src': 'iNaturalist', 'border': polys is not None,
           'n': len(quads), 'q': quads,
           's': [[name, common.get(name, ''), occ] for name, occ in sorted(species.items())]}
    with open('atlas.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Fertig: {len(quads)} Quadranten, {len(species)} Arten', file=sys.stderr)

if __name__ == '__main__':
    main()

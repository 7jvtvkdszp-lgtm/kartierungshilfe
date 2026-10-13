"""Verwechslungspaare für ganz Österreich (Wunsch von Thomas).

Holt alle Gefäßpflanzen-Arten Österreichs auf iNaturalist und je Art die dort häufigsten Verwechslungsarten.
Arten im Rechteck um die 11 Mondsee-Irrsee-Quadranten werden markiert (dort zuerst Merkmale schreiben).
Ergebnis: scripts/similar_pairs.json, Grundlage für die Merkmale in merkmale.json.
"""
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_atlas import inat, sp_name, PLACE_AT, INAT_TRACHEOPHYTA

S, N, W, E = 47.70, 48.00, 13 + 10 / 60, 13.5  # 8045/2 bis 8246/2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'similar_pairs.json')

def species(box=None):
    out, page = {}, 1
    while True:
        j = inat('observations/species_counts', {'place_id': PLACE_AT, **(box or {}),
                 'verifiable': 'true', 'taxon_id': INAT_TRACHEOPHYTA, 'per_page': 500, 'page': page})
        for r in j['results']:
            t = r.get('taxon') or {}
            if t.get('rank_level') == 10: out[t['name']] = (t['id'], r['count'])
        if page * 500 >= j['total_results']: break
        page += 1
    return out

def main():
    sp = species()
    home = set(species({'swlat': S, 'swlng': W, 'nelat': N, 'nelng': E}))
    print(f'{len(sp)} Arten in Österreich, {len(home)} im Gebiet Mondsee-Irrsee', file=sys.stderr)
    pairs = {}
    for k, (name, (tid, n)) in enumerate(sorted(sp.items())):
        j = inat('identifications/similar_species', {'taxon_id': tid, 'place_id': PLACE_AT, 'verifiable': 'true'}) or {}
        for r in (j.get('results') or [])[:6]:
            t = r.get('taxon') or {}
            if t.get('rank_level', 99) > 10 or r.get('count', 0) < 2: continue
            o = sp_name(t['name'], t['rank_level'])
            if o == name: continue
            key = tuple(sorted((name, o)))
            pairs[key] = max(pairs.get(key, 0), r['count'])
        if k % 250 == 0: print(f'{k + 1}/{len(sp)}', file=sys.stderr)
    # Zeile: [Art A, Art B, Verwechslungen, beide in Österreich, eine davon im Gebiet Mondsee-Irrsee]
    rows = sorted(([a, b, c, a in sp and b in sp, a in home or b in home] for (a, b), c in pairs.items()), key=lambda x: -x[2])
    json.dump({'t': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'n': len(sp), 'home': len(home), 'pairs': rows},
              open(OUT, 'w'), ensure_ascii=False, indent=0)
    print(f'{len(rows)} Paare', file=sys.stderr)

if __name__ == '__main__':
    main()

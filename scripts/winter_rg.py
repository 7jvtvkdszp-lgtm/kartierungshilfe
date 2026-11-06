#!/usr/bin/env python3
"""Einmalige Auswertung für die Winterliste: iNat-Meldungen mit Forschungsqualität je Gefäßpflanzenart
in Österreich, getrennt nach November, Dezember, Jänner, Februar.
  python winter_rg.py -> scripts/winter_rg.json  {t, s: {Art: [Nov, Dez, Jän, Feb]}}"""
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_atlas import inat, sp_name, PLACE_AT, INAT_TRACHEOPHYTA

def main():
    data = {}
    for i, m in enumerate((11, 12, 1, 2)):
        page = 1
        while True:
            j = inat('observations/species_counts', {'place_id': PLACE_AT, 'taxon_id': INAT_TRACHEOPHYTA, 'quality_grade': 'research',
                     'month': m, 'per_page': 500, 'page': page})
            for res in j['results']:
                t = res.get('taxon') or {}
                if not t or t.get('rank_level', 99) > 10: continue
                data.setdefault(sp_name(t['name'], t['rank_level']), [0] * 4)[i] += res['count']
            if page * 500 >= j['total_results']: break
            page += 1
        print(f'Monat {m}: fertig', file=sys.stderr)
    out = {'t': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 's': data}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'winter_rg.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(data)} Arten', file=sys.stderr)

if __name__ == '__main__':
    main()

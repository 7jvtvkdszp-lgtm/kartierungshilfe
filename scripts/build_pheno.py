#!/usr/bin/env python3
"""Beobachtungszeit je Art in Österreich für die Kartierungshilfe (Lifer-Ziele):
für jeden Halbmonat (1.–15. und 16.–Monatsende) die Zahl der iNaturalist-Meldungen je Gefäßpflanzenart.
  python build_pheno.py -> pheno.json  {v, t, s: {Art: [24 Zahlen, Jänner erste Hälfte … Dezember zweite Hälfte]}}
Läuft monatlich als GitHub Action, braucht nur die Python-Standardbibliothek."""
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_atlas import inat, sp_name, PLACE_AT, INAT_TRACHEOPHYTA

def main():
    data = {}
    for m in range(1, 13):
        for h, days in enumerate(('1,2,3,4,5,6,7,8,9,10,11,12,13,14,15', '16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31')):
            idx, page, n = (m - 1) * 2 + h, 1, 0
            while True:
                j = inat('observations/species_counts', {'place_id': PLACE_AT, 'taxon_id': INAT_TRACHEOPHYTA, 'verifiable': 'true',
                         'month': m, 'day': days, 'per_page': 500, 'page': page})
                for res in j['results']:
                    t = res.get('taxon') or {}
                    if not t or t.get('rank_level', 99) > 10: continue
                    row = data.setdefault(sp_name(t['name'], t['rank_level']), [0] * 24)
                    row[idx] += res['count']; n += 1
                if page * 500 >= j['total_results']: break
                page += 1
            print(f'Monat {m}, Hälfte {h + 1}: {n} Einträge', file=sys.stderr)
    out = {'v': 1, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 's': data}
    json.dump(out, open('pheno.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'pheno.json: {len(data)} Arten', file=sys.stderr)

if __name__ == '__main__':
    main()

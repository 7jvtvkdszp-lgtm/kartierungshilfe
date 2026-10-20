"""Ränge für den Play-Tab (Wunsch von Thomas): ranks.json aus atlas.json und scripts/inat_rg.json.

Rangliste nur über die in Österreich verifizierten Arten (iNat-Forschungsqualität, rg > 0); N = deren Anzahl.
- Quadranten-Rang: nach Zahl der bestätigten Viertelquadranten der Art im Atlas, absteigend (meiste = Rang 1).
  Unbestätigte Quadranten (fünfter Eintrag der Artzeile, ab dem Atlas vom November 2026) zählen nicht.
- Beobachtungs-Rang: nach Zahl der verifizierten iNat-Beobachtungen in Österreich, absteigend.
- Gleichstand = gleicher Platz, der nächste Platz wird übersprungen (1, 2, 2, 4).

Format: {"v": 1, "t": Erstellzeit, "a": Stand des Atlas, "n": N, "s": {Art: [qRang, qZahl, bRang, bZahl]}}
Aufruf: python scripts/build_ranks.py (im Monatslauf .github/workflows/atlas.yml nach build_atlas.py merge)
"""
import json, re, sys
from datetime import datetime, timezone

# wie TAX_FIX in index.html: diese Namen gelten in Österreich immer als die rechte Art
TAX_FIX = {'Dactylorhiza maculata': 'Dactylorhiza fuchsii'}
canon = lambda s: TAX_FIX.get(s, s)
# wie atlasKey in index.html: Schreibvarianten (Bindestrich, ×) auf einen Schlüssel
key = lambda s: re.sub(r'×|-|\s+x\s+|\s+', '', s.lower())

def ranks(values):
    """Wettkampf-Rangfolge, größter Wert = Rang 1, Gleichstand gleicher Platz (1, 2, 2, 4)."""
    order = sorted(values, key=lambda kv: -kv[1])
    out, prev, place = {}, None, 0
    for i, (n, v) in enumerate(order, 1):
        if v != prev: place, prev = i, v
        out[n] = place
    return out

def main():
    a = json.load(open('atlas.json', encoding='utf-8'))
    rg = json.load(open('scripts/inat_rg.json', encoding='utf-8'))['rg']
    # bestätigte Quadranten je Namensschlüssel (wie cleanAtlasNames in index.html: Gattungsangaben und Hybridformeln weg)
    quads = {}
    for row in a['s']:
        s = row[0]
        if re.search(r'\s(spec|sp|spp)\.?$', s, re.I) or re.match(r'^\S+ \S+ x \S+', s): continue
        occ, un = row[2], set(row[4]) if len(row) > 4 else set()
        quads.setdefault(key(canon(s)), set()).update(occ[i] for i in range(0, len(occ), 2) if occ[i] not in un)
    counts = {}
    for s, n in rg.items():
        s = canon(s)
        if n > 0: counts[s] = counts.get(s, 0) + n
    q = {s: len(quads.get(key(s), ())) for s in counts}
    qr, br = ranks(q.items()), ranks(counts.items())
    out = {'v': 1, 't': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'a': a.get('t'), 'n': len(counts),
           's': {s: [qr[s], q[s], br[s], counts[s]] for s in sorted(counts)}}
    json.dump(out, open('ranks.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'ranks.json: {len(counts)} verifizierte Arten, {sum(1 for v in q.values() if not v)} ohne bestätigten Quadranten', file=sys.stderr)

if __name__ == '__main__':
    main()

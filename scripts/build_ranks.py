"""Ränge für den Play-Tab (Wunsch von Thomas): ranks.json aus atlas.json und scripts/inat_rg.json.

Rangliste nur über die in Österreich verifizierten Arten (iNat-Forschungsqualität, rg > 0); N = deren Anzahl.
- Quadranten-Rang: nach Zahl der bestätigten Viertelquadranten der Art im Atlas, absteigend (meiste = Rang 1).
  Unbestätigte Quadranten (fünfter Eintrag der Artzeile, ab dem Atlas vom November 2026) zählen nicht.
- Beobachtungs-Rang: nach Zahl der verifizierten iNat-Beobachtungen in Österreich, absteigend.
- Gleichstand = gleicher Platz, der nächste Platz wird übersprungen (1, 2, 2, 4).

Format: {"v": 1, "t": Erstellzeit, "a": Stand des Atlas, "n": N, "s": {Art: [qRang, qZahl, bRang, bZahl]}}
Aufruf: python scripts/build_ranks.py (im Monatslauf .github/workflows/atlas.yml nach build_atlas.py merge)

Monatsverlauf (v70): bei jedem Lauf zusätzlich ranks/JJJJ-MM.json (Monat der Erstellzeit, ein späterer Lauf im selben Monat
überschreibt ihn) = {"v": 1, "m": Monat, "t", "n": N, "s": {Art: [qRang, bRang]}} mit denselben Namen wie ranks.json,
und ranks-hist.json für die App: die letzten bis zu 24 Monate, {"v": 1, "t": Erstellzeit des letzten, "m": [Monate], "n": [N je Monat],
"s": {Art: [qRang, bRang, qRang, bRang, …]}} in der Reihenfolge von m, 0 = in dem Monat nicht in der Rangliste.
python scripts/build_ranks.py --nur-verlauf legt nur Schnappschuss und Verlauf aus der vorhandenen ranks.json an.
"""
import glob, json, os, re, sys
from datetime import datetime, timezone

# wie TAX_FIX in index.html: diese Namen gelten in Österreich immer als die rechte Art
TAX_FIX = {'Dactylorhiza maculata': 'Dactylorhiza fuchsii', 'Carex pendula': 'Carex agastachys'}
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
    history(out)

HIST_MONTHS = 24

def history(out):
    """Monats-Schnappschuss ranks/JJJJ-MM.json schreiben und ranks-hist.json aus den letzten HIST_MONTHS Monaten bauen."""
    month = out['t'][:7]
    os.makedirs('ranks', exist_ok=True)
    snap = {'v': 1, 'm': month, 't': out['t'], 'n': out['n'], 's': {s: [r[0], r[2]] for s, r in out['s'].items()}}
    json.dump(snap, open(f'ranks/{month}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    files = sorted(f for f in glob.glob('ranks/*.json') if re.search(r'/\d{4}-\d{2}\.json$', f.replace(os.sep, '/')))[-HIST_MONTHS:]
    snaps = [json.load(open(f, encoding='utf-8')) for f in files]
    names = sorted({s for sn in snaps for s in sn['s']})
    hist = {'v': 1, 't': snaps[-1]['t'], 'm': [sn['m'] for sn in snaps], 'n': [sn['n'] for sn in snaps],
            's': {s: [x for sn in snaps for x in sn['s'].get(s, [0, 0])] for s in names}}
    json.dump(hist, open('ranks-hist.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'ranks/{month}.json, ranks-hist.json: {len(snaps)} Monat(e), {len(names)} Arten', file=sys.stderr)

if __name__ == '__main__':
    if '--nur-verlauf' in sys.argv: history(json.load(open('ranks.json', encoding='utf-8')))
    else: main()

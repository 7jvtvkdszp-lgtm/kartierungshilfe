# Kartierungshilfe

Web-App fürs iPhone: bestimmt per GPS den Quadranten der Floristischen Kartierung Österreichs (z. B. 8146/1) und zeigt, ob eine Art dort in den eigenen iNaturalist-Funden (Standard: mondseeirrsee) schon vorkommt.

## Dateien (Repository-Wurzel)
- `index.html` – die ganze App (HTML, CSS, JS in einer Datei)
- `sw.js` – Service Worker, damit die App ohne Empfang startet. Bei Änderungen `VERSION` erhöhen.
- `manifest.webmanifest`, `icon-*.png` – für „Zum Home-Bildschirm“

## Funktionen
- **Prüfen:** Quadrant per GPS, Status der Art im Quadranten (kartiert / nach 3 Jahren wieder fällig / neu), Kürzelsuche („aju rep“), Fundchance, Rote Liste, Saison, Entfernung zum nächsten Fund aller iNaturalist-Nutzer, „+ Auf die Tagesliste“.
- **Arten:** eigene Arten je Quadrant (grün/orange), Abdeckung in %, „Noch nicht gefunden“ sortiert nach Saison und Fundchance.
- **Karte:** OSM mit Raster (Grundfelder fett, beschriftet), Quadranten nach Abdeckung eingefärbt; Offline-Paket für das sichtbare Gebiet; „Lohnende Quadranten“ im Umkreis 5–50 km (Lifer = in Österreich noch nie gefunden haben Vorrang, dann offene Arten nach Häufigkeit, Saison zählt 1,5-fach); Lifer auch in der Artenliste markiert und zuerst.
- **Rote Liste Österreich** (Stapfia 114, 2022; `rl.json` aus `scripts/rl_source.json` per GitHub Action „Rote Liste aufbereiten“, Namen auf iNaturalist abgeglichen): Kategorie als Chip (RL EN …), regional stärkere Gefährdung, Endemiten, und je Bundesland des Quadranten „neu für OÖ“ (Erstnachweis-Kandidat) bzw. „Wiederfund“ (dort verschollen). Naturräume (AL, BM, NV, SV, PA) je Quadrant in `naturraum.json`, aus der Naturraumkarte der Roten Liste über die Kartenfarben zugeordnet (Lambert-Projektion, Passung auf etwa 1 km). Berührt ein Quadrant mehrere Bundesländer oder Naturräume, nennt die App jedes, in dem die Art fehlt. Neu einlesen: `python scripts/rl_parse.py tabelle.xlsx` (braucht openpyxl).
- **Häufigkeit** (Arten): Auswahl H10–H1, alle Arten der Klasse nach Entfernung zum nächsten Quadranten mit Funden, optional nur Lifer. Klassen: Arten mit nur einer Meldung in Österreich = H10, die übrigen nach Quadrantenzahl als Glockenkurve auf H1–H9 (0,5 σ je Klasse). Hybriden bekommen keine Klasse. Einzelmeldungen ohne iNat-Forschungsqualität sind schon im Atlas weggelassen.
- **Lifer-Ziele** (Karte): Lifer nach Zahl der Österreich-Meldungen, bestes Zeitfenster (Halbmonat mit den meisten Meldungen, `pheno.json` per Action „Beobachtungszeiten aktualisieren“), nächster Quadrant mit Funden (Atlas), genauer Fundpunkt auf Knopfdruck, Mitnahme-Lifer rund um diesen Quadranten mit passendem Zeitfenster.
- **Offline:** Gebiet (Mitte + 5–30 km) vorab laden: „jetzt“ und „bald vorbei“ je Block von 5 × 5 Quadranten, Arten aller Nutzer nur außerhalb der Österreich-Daten. Liste vorbereiteter Gebiete mit Status je Monat.
- **Heute:** digitale Strichliste des aktuellen Quadranten (Antippen = gesehen, gerade beobachtbare Arten zuerst, Suche über alle Arten Österreichs) mit Begleitarten aus dem Atlas (oft gemeinsam vorkommend, hier noch offen); Tagesliste, wird automatisch abgehakt, sobald der Fund auf iNaturalist ist. Im Prüfergebnis „Oft zusammen mit“.
- **Mitlaufen:** verfolgt die Position und meldet mit Ton und Hinweis den Wechsel in einen neuen Quadranten (nur bei geöffneter App; iPhone erlaubt Web-Apps keine Vibration).
- **Feldhilfen (v19):** Grenzwarnung, wenn die GPS-Genauigkeit größer ist als der Abstand zur Quadrantengrenze; Vergleichsfoto und häufige Verwechslungsarten (iNat similar_species, Österreich) im Prüfergebnis; Wunschliste (Tab Heute) mit Hinweis, wenn eine Wunschart im Quadranten bekannt ist; „Neu in der Umgebung“: Lifer, die andere im Umkreis von 30 km neu hochgeladen haben; Karte wahlweise nach Lifern eingefärbt.
- **v37:** Häufigkeitsklassen als Normalverteilung, Einzelmeldungen in H10.
- **v36:** Häufigkeitsklassen nach Prozent der Quadranten statt Rang, ohne Hybriden. Taxonomische Festlegungen (`TAX_FIX` in index.html): Dactylorhiza maculata zählt in Österreich als D. fuchsii (eigene Funde, Gebietsdaten, Atlas, Beobachtungszeiten).
- **v20:** Löschknopf (×) in Suchfeldern; „Tipps für den Quadranten“ (wahrscheinlichster Lifer, wahrscheinlichste noch nicht kartierte Art, am längsten nicht kartierte Art); Häufigkeitsklasse H1–H10 (Dezile nach Zahl der österreichischen Quadranten mit iNat-Beobachtungen) und Verbreitungskarte (Anteil der Quadranten im Umkreis 30 km). Datengrundlage `atlas.json` (iNaturalist + GBIF der letzten 20 Jahre, nur Gefäßpflanzen, GBIF-Namen auf iNat-Taxonomie abgeglichen; ergänzt auch Artenlisten, Fundchance, Karte und lohnende Quadranten), monatlich erstellt von `.github/workflows/atlas.yml` mit `scripts/build_atlas.py`.
- **v22:** Artenliste „Erwartet“ (in ≥60 % der Nachbarquadranten bekannt, hier nie gemeldet), Kartenmodus „Lücken“ (bekannte Arten im Verhältnis zum Median der zwei Ringe ringsum), Lifer-Tour (iNat-Fundpunkte anderer, nur ±14 Tage um das heutige Datum, Nächster-Nachbar-Reihenfolge, Google-Maps-Gesamtroute), Wunschliste gilt je Quadrant.
- **v23:** nur Gefäßpflanzen (iNat taxon_id 211194 Tracheophyta: ohne Moose und Algen wie Chara oder Trentepohlia); Lifer-Statistik unter Daten (Lifer je Jahr, sortierbar, je Monat, erfolgreichster Monat).
- **v24:** „Jetzt oder nie“: Arten, die im Umkreis (5×5 Quadranten) diesen Monat ≥2× gemeldet sind, im nächsten Monat ≤20 % davon; Chip „bald vorbei“, Abschnitt in den Tipps.
- **Daten:** offene Bestimmungen (nur Gattung / Needs ID; Gattungsfunde zählen nicht als kartiert), Jahresbilanz (Funde, Erstnachweise je Quadrant, am längsten nicht besuchte Quadranten), Sicherung/Wiederherstellung als JSON (ohne Token).
- **Export für observation.org:** CSV (Semikolon, UTF-8): species;date;time;lat;lng;accuracy;abundance;remarks.

## Raster
Grundfeld 10′ Länge × 6′ Breite, Zeile = floor((56 − Breite) × 10), Spalte = floor((Länge − 5°40′) × 6).
Viertel 1 NW, 2 NO, 3 SW, 4 SO. Geprüft gegen 13 Quadranten-Mittelpunkte aus dem GBIF-Datensatz
„Floristische Kartierung Österreichs“ (alle korrekt).

## Daten
- Live von der iNaturalist-API (v1/observations, nur Gefäßpflanzen, Unterarten werden zur Art zusammengefasst), gespeichert im Browser (localStorage), danach offline nutzbar.
- „Funde aktualisieren“ lädt nur Änderungen seit dem letzten Abgleich, „Alles neu laden“ auch Löschungen.
- Verschleierte Koordinaten: mit API-Token (inaturalist.org/users/api_token, 24 h gültig) kommen die genauen eigenen Koordinaten; alternativ CSV-Export importieren.

## Online stellen
Die App braucht eine eigene https-Adresse (für GPS, Offline-Cache und den Zugriff auf iNaturalist).

**Variante A, ohne Konto-Einrichtung am Computer:** app.netlify.com/drop öffnen und den Ordner `app` hineinziehen. Man bekommt sofort eine Adresse.

**Variante B, GitHub Pages (empfohlen für laufende Updates):** Repository anlegen, Inhalt von `app/` hochladen, unter Settings → Pages den Branch `main` aktivieren. Ist GitHub mit Claude verbunden, kann Claude Updates direkt einspielen.

Danach auf dem iPhone die Adresse in Safari öffnen → Teilen → „Zum Home-Bildschirm“. Einmal mit Empfang öffnen und unter „Daten“ die Funde laden.

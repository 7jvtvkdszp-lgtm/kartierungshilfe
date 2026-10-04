# Kartierungshilfe

Web-App fürs iPhone: bestimmt per GPS den Quadranten der Floristischen Kartierung Österreichs (z. B. 8146/1) und zeigt, ob eine Art dort in den eigenen iNaturalist-Funden (Standard: mondseeirrsee) schon vorkommt.

## Dateien (Repository-Wurzel)
- `index.html` – die ganze App (HTML, CSS, JS in einer Datei)
- `sw.js` – Service Worker, damit die App ohne Empfang startet. Bei Änderungen `VERSION` erhöhen.
- `manifest.webmanifest`, `icon-*.png` – für „Zum Home-Bildschirm“

## Raster
Grundfeld 10′ Länge × 6′ Breite, Zeile = floor((56 − Breite) × 10), Spalte = floor((Länge − 5°40′) × 6).
Viertel 1 NW, 2 NO, 3 SW, 4 SO. Geprüft gegen 13 Quadranten-Mittelpunkte aus dem GBIF-Datensatz
„Floristische Kartierung Österreichs“ (alle korrekt).

## Daten
- Live von der iNaturalist-API (v1/observations, nur Plantae, Unterarten werden zur Art zusammengefasst), gespeichert im Browser (localStorage), danach offline nutzbar.
- „Funde aktualisieren“ lädt nur Änderungen seit dem letzten Abgleich, „Alles neu laden“ auch Löschungen.
- Verschleierte Koordinaten: mit API-Token (inaturalist.org/users/api_token, 24 h gültig) kommen die genauen eigenen Koordinaten; alternativ CSV-Export importieren.

## Online stellen
Die App braucht eine eigene https-Adresse (für GPS, Offline-Cache und den Zugriff auf iNaturalist).

**Variante A, ohne Konto-Einrichtung am Computer:** app.netlify.com/drop öffnen und den Ordner `app` hineinziehen. Man bekommt sofort eine Adresse.

**Variante B, GitHub Pages (empfohlen für laufende Updates):** Repository anlegen, Inhalt von `app/` hochladen, unter Settings → Pages den Branch `main` aktivieren. Ist GitHub mit Claude verbunden, kann Claude Updates direkt einspielen.

Danach auf dem iPhone die Adresse in Safari öffnen → Teilen → „Zum Home-Bildschirm“. Einmal mit Empfang öffnen und unter „Daten“ die Funde laden.

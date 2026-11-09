# Peer-Auswertung und Netzwerkverkehr

Deutsch | [English](en/NODE_INSIGHTS.md)

Ab Version 1.20.0 enthält der Reiter **Netzwerk** Verkehrsraten und die
eingeklappte Tabelle **Peer-Software und Fähigkeiten**. **Historie** zeigt
den Bitcoin-Core-Traffic nach Kalendertagen. Unter **Analyse** stehen die letzten
20 lokal erfassten Blöcke. Für die Funktionen bis 1.23 werden keine zusätzlichen RPC-Methoden benötigt; die neue Blockauslastung ab 1.25 benötigt `getblock`.

## Diagramme ab 1.25

Unter **Netzwerk → Traffic nach Nachrichtentyp** stehen zwei gestapelte Flächendiagramme für Empfang und Versand (dezimal KB/s) sowie die erfassten Byte-Summen des gewählten Zeitraums. Gruppen:

- Blöcke: `block`, `cmpctblock`, `blocktxn`, `getblocktxn`.
- Transaktionen: `tx`.
- Ankündigungen und Anfragen: `inv`, `getdata`, `notfound`, `getblocks` (gemischte Inhalte; `getblocks` fordert eine Block-Inventarliste an).
- Blockheader: `headers`, `getheaders`.
- Weitere Nachrichten: alle übrigen Typen, einschließlich Protokollverwaltung.

Einmal pro Messintervall werden `getpeerinfo` und `uptime` gelesen. Deltas gelten nur für dieselbe Peer-ID und Verbindungsstartzeit, nicht sinkende Einzelzähler und passende Core-Laufzeit. Zu große Zeitlücken oder Neustarts werden nicht überbrückt. Neue, getrennte oder nicht vergleichbare Verbindungen fehlen in den Summen. Auch unbemerkt zwischen zwei Messungen gestartete und beendete Verbindungen fehlen. Die Werte sind daher ein erfasster Teil des P2P-Anwendungsverkehrs, kein vollständiger Node- oder Provider-Traffic. Null ist gemessener Stillstand; unbekannte Werte bleiben leer.

Nur aggregierte Gruppenwerte werden in `message_traffic_samples` gespeichert. Peer-Identitäten bleiben ausschließlich in der flüchtigen Vergleichsbasis; IP-Adressen werden dafür weder gespeichert noch veröffentlicht. Nach einem Dashboard-Neustart benötigt die Erfassung zwei neue Messungen. Zeitabschnitte mit ungültigen Messungen bleiben im Diagramm unbekannt. Raten werden über die gültige Messdauer gewichtet; Randintervalle werden nicht anteilig erfunden. Die Summen können trotz unbekannter Diagrammabschnitte gültige Teilintervalle enthalten.

Unter **Analyse → Gebührenband und Blockauslastung** zeigen P10/P25/P50/P75/P90 die nach Transaktionsgewicht gewichteten Gebührenraten aus `getblockstats` in sat/vB. P50 ist der Median; P10–P90 und P25–P75 erscheinen als farbige Bänder. Das sind bestätigte Gebühren, keine Empfehlung oder Prognose. Je Diagrammzeitabschnitt wird der letzte erfasste Block gewählt; Perzentile werden nicht gemittelt.

Das vollständige Gewicht aus `getblock` enthält die Coinbase-Transaktion. Auslastung = Gewicht / 4.000.000 × 100 %. `getblockstats.total_weight` allein wäre unvollständig, weil es Coinbase ausschließt. Fehlen Daten oder ist ein Block geprunt, bleibt sein Wert unbekannt. Bestehende ältere Beobachtungen erhalten keine erfundene Historie; der aktuelle Block kann ergänzt werden. Die globale Zeitraumwahl unter **Historie** gilt für beide neuen Ansichten.

### Einrichtung und Update

Für die neue Lesemethode `getblock` den Root-Bootstrap aus dem geprüften aktuellen Release erneut ausführen, siehe [Sicherheitsmigration](SECURITY.md). Er ergänzt die vorhandene RPC-Freigabe ohne neue Zugangsdaten und startet den lokalen Core nur bei geänderter Freigabe neu; das Dashboard wird ebenfalls neu gestartet. Ein reines Dashboard-Update kann das Gebührenband bereits erfassen, lässt die Blockauslastung ohne diese Freigabe aber unbekannt. Externe Nodes benötigen die Freigabe auf ihrem eigenen Host. Keine neuen Python- oder Systempakete nötig. Container mit vollständigen Cookie-Rechten benötigen keine zusätzliche RPC-Freigabe; eingeschränkte Konten entsprechend ergänzen.

## Peer-Details

Clientnamen und Softwareversionen stammen aus `getpeerinfo.subver`, nicht aus
der P2P-Protokollnummer. Es erscheinen maximal zwölf Clientgruppen und eine
Restgruppe. Freie Kommentare und fremde Peer-Adressen werden nicht ausgegeben.
Die Werte sind Selbstauskünfte anderer Nodes und kein verifizierter Fingerabdruck.

Service-Flags zeigen angebotene Fähigkeiten: NETWORK (vollständige Blockhistorie),
NETWORK_LIMITED (letzte Blöcke), WITNESS (SegWit), BLOOM (Bloom-Filter),
COMPACT_FILTERS (kompakte Blockfilter), P2P_V2 (verschlüsselter Transport).
Ein Peer kann mehrere Fähigkeiten haben; die Summe der Flag-Zähler kann deshalb
größer als die Peer-Anzahl sein. P2P_V2 bedeutet Unterstützung; die bestehende
Transport-v2-Anzeige zählt dagegen tatsächlich verwendeten Transport v2.

Verbindungsarten unterscheiden In, Out mit Full relay oder Block relay,
manuelle Verbindungen und kurzlebige Feeler-/Adressabfragen. Unbekannte oder
datenschutzrelevante weitere Arten werden zusammengefasst, nicht einzeln benannt.
Die Auswertung nutzt die bestehenden Momentaufnahmen und historisiert keine
individuellen Peer-Verbindungen.

## Verkehr und Datenqualität

Die Live-Raten in KiB/s sind Differenzen der Core-Zähler aus `getnettotals`,
geteilt durch die Zeit zwischen zwei Abfragen. Die erste Abfrage, fehlende Werte,
ein Zählerrückgang, ein erkannter Neustart oder eine zu große Zeitlücke ergeben
**unbekannt**, nicht null. Null steht für ein gültig gemessenes Intervall ohne
Verkehr. Die bestehenden Gesamtzähler gelten seit dem letzten Core-Start.

Die Historie nutzt vorhandene SQLite-Messungen. Nur Intervalle bis maximal
`max(120, 3 × SAMPLE_INTERVAL_SECONDS)` Sekunden mit kontinuierlich steigender
Core-Laufzeit und nicht fallenden Zählern zählen. Die Laufzeit darf höchstens
fünf Sekunden vom Messintervall abweichen. Die violette Spitzenlinie zeigt
für jeden Tag die höchste gültige Uploadrate zwischen zwei Messpunkten.

Unter **Bitcoin-Core-Traffic nach Tagen** stehen Download, Upload,
zeitgewichtete Verbindungszahl, Uploadspitze und Messabdeckung pro Kalendertag.
Die Datenmengen verwenden dezimale Einheiten mit 1 GB = 1.000 MB.
Die Tabelle folgt dem gewählten Zeitraum und der angezeigten Browserzeitzone.
Angefangene Tage zeigen den innerhalb des gewählten Zeitraums liegenden Anteil.
Grenzintervalle werden ausgelassen. Bei einer Zeitumstellung kann ein Tag 23
oder 25 Stunden dauern.
Messabdeckung bedeutet gültige gemessene Sekunden geteilt durch die Dauer des
Zeitraums bis jetzt. Fehlende Messungen, Aufbewahrungsgrenzen und ausgeschaltete
Nodes können zu niedriger Abdeckung führen. Die Summen sind keine Abrechnung und
kein Ersatz für Provider-Trafficdaten. Ein Neustart ist allein anhand von Zählern
und Laufzeit nicht in jedem theoretischen Fall erkennbar.

### Wochenvergleich und CSV-Bericht

Der aufklappbare Wochenvergleich umfasst die letzten sieben abgeschlossenen
Kalendertage und die sieben Tage davor. Der heutige Tag bleibt dabei außen vor.
Die Tabelle nennt je Zeitraum gemessenen Download und Upload, Upload pro Tag
(gemessene Uploadsumme geteilt durch sieben), den stärksten gemessenen Uploadtag
und die zeitliche Messabdeckung. Eine prozentuale Uploadänderung erscheint ab
90 % Abdeckung in beiden Zeiträumen und bei einem positiven Vergleichswert.
Fehlende Daten können die gemessenen Mengen verringern.

**CSV-Bericht herunterladen** exportiert die Tage im gewählten Historienzeitraum.
Der UTF-8-Download enthält Byte-Mengen, Spitzenrate in Bytes pro Sekunde,
Peer-Zahlen, Messdauer, IPv4-/IPv6-/Tor-Mittelwerte und erfasste Blockstatistiken.
Die Spaltennamen sind sprachunabhängig auf Englisch. Zahlen verwenden einen
Dezimalpunkt, unbekannte Werte bleiben leer. Zeitgrenzen sind lokale ISO-Zeitwerte
einschließlich UTC-Offset und Zeitzonenname. Die Berechnung nutzt die bereits
geladenen Daten.

### Netzwerkverlauf und tägliche Blockstatistik

**Netzwerkverlauf** zeigt unter Historie je ein Diagramm für IPv4, IPv6 und Tor
mit In und Out. Die Werte sind mittlere Anzahlen der gespeicherten Momentaufnahmen
je Diagrammabschnitt. Sechs zusätzliche nullable SQLite-Spalten erfassen die
Anzahlen ab Version 1.23.0. Ältere Messpunkte behalten unbekannte Netzwerkwerte.
Bekannte Lücken im Verlauf unterbrechen die Linien.

Unter Analyse steht die **Tägliche Blockstatistik**. Ein Eintrag pro gespeicherter
Blockhöhe zählt einmal. Die Tabelle gruppiert anhand der Blockzeit in der
Browserzeitzone und zeigt erfasste Blöcke, Transaktionssumme, durchschnittliche
Blockgröße und Gebührensumme. Fehlt ein Einzelwert, bleibt die entsprechende
Tageskennzahl unbekannt. Die Tabelle umfasst die lokal gespeicherten Beobachtungen
im gewählten Zeitraum. Nachtragsgrenzen und Reorganisationen begrenzen ihre
Vollständigkeit.

`GET /api/traffic?range=24h` verwendet dieselben sieben erlaubten Zeiträume wie
die Historie. Unbekannte Werte fallen auf 24h zurück. Der optionale Parameter
`timezone` akzeptiert eine IANA-Zeitzone wie `Europe/Berlin`. Ohne gültige
Zeitzone verwendet die API UTC. Bestehende Zeitraum-, Tages- und Monatssummen
sowie die feineren Raten bleiben über die API verfügbar.
SQLite berechnet Differenzen und Zeitabschnitte.
Pro Zeitraum wird das letzte Ergebnis 30 Sekunden gecacht.
Die API liest keine individuellen Peer-Adressen und erlaubt keine RPC-Aufrufe.

## Erfasste Blöcke

`GET /api/recent-blocks` liefert höchstens 20 gespeicherte `block_observations`,
absteigend nach Höhe: Blockzeit, Transaktionen, Größe und Gebühren in BTC.
Fehlende Werte bleiben unbekannt. Die bestehende Erfassung und ihr begrenzter
Nachtrag bestimmen den Umfang; neue Installationen zeigen zunächst weniger Blöcke.
Die Tabelle ist kein vollständiger Explorer und keine unveränderliche Reorg-Chronik.

Die Implementierung wurde eigenständig anhand der vorhandenen Daten und der
offiziellen Bitcoin-Core-RPC-Schnittstellen entwickelt; fremder Dashboard-Code
wird nicht übernommen.

[Zurück zur Übersicht](../README.md)

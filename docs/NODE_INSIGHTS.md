# Peer-Auswertung und Netzwerkverkehr

Deutsch | [English](en/NODE_INSIGHTS.md)

Ab Version 1.20.0 enthält der Reiter **Netzwerk** Verkehrsraten und die
eingeklappte Tabelle **Peer-Software und Fähigkeiten**. **Historie** zeigt
Verkehrsraten und gemessene Summen. Unter **Analyse** stehen die letzten
20 lokal erfassten Blöcke. Es werden keine zusätzlichen RPC-Methoden benötigt.

## Peers

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
fünf Sekunden vom Messintervall abweichen. In einem Diagramm-Zeitabschnitt mit
ungültigem Intervall bleibt die Rate unbekannt. Gültige Raten werden nach der
gemessenen Zeit gewichtet.

Summen für den gewählten Zeitraum, heute und den laufenden Monat enthalten nur
vollständig innerhalb der jeweiligen Grenzen gemessene Intervalle. Tag und Monat
beginnen um 00:00 UTC; Grenzintervalle werden ausgelassen, nicht geschätzt.
Messabdeckung bedeutet gültige gemessene Sekunden geteilt durch die Dauer des
Zeitraums bis jetzt. Fehlende Messungen, Aufbewahrungsgrenzen und ausgeschaltete
Nodes können zu niedriger Abdeckung führen. Die Summen sind keine Abrechnung und
kein Ersatz für Provider-Trafficdaten. Ein Neustart ist allein anhand von Zählern
und Laufzeit nicht in jedem theoretischen Fall erkennbar.

`GET /api/traffic?range=24h` verwendet dieselben sieben erlaubten Zeiträume wie
die Historie; unbekannte Werte fallen auf 24h zurück. SQLite berechnet Differenzen
und Zeitabschnitte; maximal sieben Ergebnisse werden jeweils 30 Sekunden gecacht.
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

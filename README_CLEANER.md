
# DXF Cleaner für Laserschneiden

Dieses Skript automatisiert die Vorbereitung von DXF-Zeichnungen für CNC-Maschinen (Laser, Plasma, Wasserstrahl).

## Funktionen

1.  **Bereinigung**: Entfernt Text, Bemaßungen und andere nicht-geometrische Elemente.
2.  **Deduplizierung**: Entfernt doppelte Linien.
3.  **Topologie-Korrektur**:
    - Findet zusammenhängende Konturen.
    - Schließt Lücken in Konturen automatisch, wenn sie kleiner als 1.0mm sind.
    - Konvertiert Kreise und Bögen in optimierte Polylinien.
4.  **Feedback**:
    - Setzt visuelle Marker (kleine magentafarbene Kreise) an Stellen, wo Lücken automatisch geschlossen wurden.
    - Gibt einen Bericht auf der Konsole aus.
5.  **Output**:
    - Erzeugt eine saubere DXF-Datei (R2010).
    - Alle Schneidkonturen liegen auf dem Layer `SCHNITT_CONTUR`.

## Installation

Benötigt Python 3 und `ezdxf`:

```bash
pip install ezdxf
```

## Nutzung

```bash
python dxf_cleaner.py
```

Das Skript sucht aktuell nach `dirty_input.dxf` und schreibt `clean_output.dxf`.
(Im Produktivbetrieb würde man Argumente übergeben).

## Anpassung

Im Skript `dxf_cleaner.py` können folgende Parameter angepasst werden:

- `gap_tol`: Maximale Lückengröße, die geschlossen wird (Default: 1.0mm).
- `target_layer`: Layername für die Konturen.
- `marker_layer`: Layername für die Warn-Marker.

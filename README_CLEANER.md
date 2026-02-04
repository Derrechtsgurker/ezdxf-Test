
# DXF Cleaner für Laserschneiden

Dieses Skript automatisiert die Vorbereitung von DXF-Zeichnungen für CNC-Maschinen (Laser, Plasma, Wasserstrahl).

## Funktionen

1.  **Bereinigung**: Entfernt Text, Bemaßungen und andere nicht-geometrische Elemente.
2.  **Deduplizierung**: Entfernt doppelte Linien.
3.  **Topologie-Korrektur**:
    - Findet zusammenhängende Konturen.
    - Schließt Lücken in Konturen automatisch, wenn sie kleiner als die Toleranz (Default: 1.0mm) sind.
    - Konvertiert Kreise und Bögen in optimierte Polylinien.
4.  **Feedback**:
    - Setzt visuelle Marker (kleine magentafarbene Kreise) an Stellen, wo Lücken automatisch geschlossen wurden.
    - Gibt einen Bericht auf der Konsole aus.
5.  **Output**:
    - Erzeugt eine saubere DXF-Datei (R2010).
    - Alle Schneidkonturen liegen auf dem Layer `SCHNITT_CONTUR` (konfigurierbar).

## Installation

Benötigt Python 3 und `ezdxf`:

```bash
pip install ezdxf
```

## Nutzung

```bash
# Standardnutzung (sucht dirty_input.dxf -> clean_output.dxf)
python dxf_cleaner.py

# Eigene Dateien angeben
python dxf_cleaner.py kunde_zeichnung.dxf maschine_ready.dxf

# Mit angepasster Toleranz (z.B. nur Lücken < 0.5mm schließen)
python dxf_cleaner.py kunde.dxf fertig.dxf --gap 0.5

# Mit anderem Ziel-Layer
python dxf_cleaner.py kunde.dxf fertig.dxf --layer CUT_LAYER_1
```

## Hilfe

Für eine Übersicht aller Optionen:

```bash
python dxf_cleaner.py --help
```

import ezdxf
from ezdxf import edgeminer as em

def verify_output(filename):
    print(f"--- Verifiziere {filename} ---")
    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()

    # 1. Prüfen auf Text/Dimensionen
    forbidden = msp.query('TEXT MTEXT DIMENSION')
    if len(forbidden) > 0:
        print(f"[FAIL] Noch {len(forbidden)} verbotene Elemente gefunden!")
    else:
        print("[OK] Keine Texte/Bemaßungen gefunden.")

    # 2. Layer prüfen
    polylines = msp.query('LWPOLYLINE')
    print(f"Anzahl Polylinien: {len(polylines)}")

    for pl in polylines:
        layer = pl.dxf.layer
        closed = pl.closed
        points = list(pl.get_points(format="xy"))
        start = points[0]
        end = points[-1]

        # Ein geschlossenes Rechteck hat ca Umfang 40 (10x10)
        # Ein fast geschlossenes Rechteck auch.
        # Ein offenes hat Umfang 30 + 8.5 = 38.5 (Fall 2)

        # Grobe Bounding Box Analyse
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)

        # Fall 1: Rechteck bei x=0 (sollte geschlossen sein)
        if -1 < min_x < 1:
            if closed:
                print(f"[OK] Kontur bei x=0 ist geschlossen. (Layer: {layer})")
            else:
                print(f"[FAIL] Kontur bei x=0 ist OFFEN! (Distanz Start-Ende: {start.distance(end):.4f})")

        # Fall 2: Rechteck bei x=20 (sollte offen sein)
        if 19 < min_x < 21:
            if not closed:
                print(f"[OK] Kontur bei x=20 ist offen. (Layer: {layer})")
            else:
                print(f"[FAIL] Kontur bei x=20 ist GESCHLOSSEN (Falsch!)")

    # 3. Marker prüfen
    markers = msp.query(f'CIRCLE[layer=="MARKER_WARNING"]')
    print(f"Anzahl Marker gefunden: {len(markers)}")
    if len(markers) > 0:
        for m in markers:
            print(f"  -> Marker bei {m.dxf.center}")
    else:
        print("[INFO] Keine Marker gefunden.")

if __name__ == "__main__":
    verify_output("clean_output.dxf")

import ezdxf
from ezdxf import colors
from ezdxf import edgeminer as em
from ezdxf import edgesmith as es
from typing import List, Tuple
import sys

def cleanup_dxf(input_file: str, output_file: str,
                gap_tol: float = 1.0,
                target_layer: str = "SCHNITT_CONTUR",
                marker_layer: str = "MARKER_WARNING"):

    print(f"--- Starte Reinigung von {input_file} ---")

    try:
        doc = ezdxf.readfile(input_file)
    except Exception as e:
        print(f"Fehler beim Lesen der Datei: {e}")
        sys.exit(1)

    msp = doc.modelspace()

    # ---------------------------------------------------------
    # Schritt 2: Unnötige Entities löschen (Text, Dimensionen)
    # ---------------------------------------------------------
    to_delete = []
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype in ("TEXT", "MTEXT", "DIMENSION", "LEADER", "MULTILEADER"):
            to_delete.append(entity)

    for entity in to_delete:
        msp.delete_entity(entity)

    print(f"Gelöscht: {len(to_delete)} Text/Bemaßung-Elemente.")

    # ---------------------------------------------------------
    # Schritt 3 & 4: Geometrie filtern & Deduplizierung (implizit durch EdgeMiner)
    # ---------------------------------------------------------
    # Wir sammeln alle Kanten ein. EdgeMiner ignoriert automatisch, woher sie kommen (Layer, Farbe etc.)
    # und betrachtet nur die Geometrie.

    # entities = msp.query('LINE ARC LWPOLYLINE POLYLINE ELLIPSE SPLINE')
    # Wir nutzen edges_from_entities_2d, das filtert bereits geeignete Entities

    input_edges = list(es.edges_from_entities_2d(msp, gap_tol=1e-6))
    print(f"Gefundene Geometrie-Kanten (Raw): {len(input_edges)}")

    # ---------------------------------------------------------
    # Sonderfall: Kreise (CIRCLE)
    # ---------------------------------------------------------
    # EdgeMiner ignoriert geschlossene Kreise, da sie keine Kanten mit offenen Enden sind.
    # Wir müssen sie separat einsammeln und direkt übertragen.
    circles = msp.query('CIRCLE')
    print(f"Gefundene Kreise (Löcher): {len(circles)}")

    # ---------------------------------------------------------
    # Schritt 5: Kettenbildung & Schließen
    # ---------------------------------------------------------

    # Deposit erstellen mit der geforderten Toleranz zum Schließen von Lücken
    deposit = em.Deposit(input_edges, gap_tol=gap_tol)

    # Duplikate filtern (deckungsgleiche Linien)
    # EdgeMiner Deposit behandelt Kanten per ID.
    # Wir nutzen filter_coincident_edges um echte Duplikate zu finden.
    unique_edges = em.filter_coincident_edges(deposit)
    print(f"Kanten nach Deduplizierung: {len(unique_edges)}")

    # Neues Deposit mit bereinigten Kanten
    clean_deposit = em.Deposit(unique_edges, gap_tol=gap_tol)

    # Wir suchen nach:
    # 1. Geschlossenen Loops (Idealfall)
    # 2. Offenen Ketten, die wir schließen können (wenn Lücke <= gap_tol)
    # 3. Offenen Ketten, die offen bleiben müssen (Lücke > gap_tol)

    loops = list(em.find_all_loops(clean_deposit))
    open_chains = list(em.find_all_open_chains(clean_deposit))

    print(f"Gefundene geschlossene Konturen: {len(loops)}")
    print(f"Gefundene offene Ketten: {len(open_chains)}")

    # Vorbereitung für die Ausgabe
    # Wir erstellen ein NEUES Dokument, um wirklich "sauber" zu sein.
    new_doc = ezdxf.new("R2010")
    new_msp = new_doc.modelspace()

    # Layer anlegen
    if target_layer not in new_doc.layers:
        new_doc.layers.add(target_layer, color=colors.WHITE)

    if marker_layer not in new_doc.layers:
        new_doc.layers.add(marker_layer, color=colors.MAGENTA)

    # Attribute für die neuen Polylinien
    poly_attribs = {"layer": target_layer}

    closed_gaps_count = 0

    # A) Kreise (die wir oben separat gefunden haben)
    for circle in circles:
        # Wir konvertieren Kreise in LWPOLYLINES, damit alles einheitlich ist.
        # Ein Kreis ist eine Polylinie mit 2 Vertexen und Bulge=1 (Halbkreis)
        # Oder einfacher: path.make_path(circle).to_lwpolyline()
        from ezdxf import path
        try:
             # Umwandlung in Pfad und dann in Polyline
             p = path.make_path(circle)
             # flattening distance kontrolliert die Auflösung, wenn wir keine Bulges wollen.
             # Aber wir wollen perfekte Kreise -> nutzen wir to_lwpolyline() wenn möglich oder erstellen manuell
             # Einfacher Weg: Wir fügen sie als CIRCLE hinzu oder konvertieren.
             # Für Maschinen ist LWPOLYLINE mit Bulges oft am besten.

             # Manuelle Konvertierung für sauberen Code ohne Abhängigkeit von flatten
             center = circle.dxf.center
             radius = circle.dxf.radius
             # Polyline mit 2 Halbkreisen
             p1 = (center.x - radius, center.y)
             p2 = (center.x + radius, center.y)

             # Wir setzen Punkte mit Format "xyb" (x, y, bulge)
             # Punkt 1: Start -> Bulge 1.0 (Halbkreis zum nächsten Punkt)
             # Punkt 2: Ende -> Bulge 1.0 (Halbkreis zurück zum Start, da closed=True)
             points = [
                 (p1[0], p1[1], 1.0),
                 (p2[0], p2[1], 1.0)
             ]
             pl = new_msp.add_lwpolyline(points, format="xyb", dxfattribs=poly_attribs)
             pl.close(True)

        except Exception as e:
            print(f"Fehler beim Konvertieren von Kreis: {e}")

    # B) Geschlossene Loops (aus EdgeMiner)
    for loop in loops:
        # Check ob der Loop wirklich geometrisch geschlossen war oder durch Toleranz geschlossen wurde
        # Loop edges sind sortiert. Start von Edge 0 und Ende von Edge -1 sollten verbunden sein.
        start_pt = loop[0].start
        end_pt = loop[-1].end
        dist = start_pt.distance(end_pt)

        if dist > 1e-4: # Kleine Toleranz für numerisches Rauschen
             # Das war eine Lücke, die Edgeminer als geschlossen betrachtet hat
             closed_gaps_count += 1
             mid_gap = start_pt.lerp(end_pt, 0.5)
             new_msp.add_circle(mid_gap, radius=gap_tol/2.0, dxfattribs={"layer": marker_layer, "color": colors.MAGENTA})
             print(f"  -> Loop-Lücke automatisch geschlossen bei {mid_gap}, Abstand: {dist:.4f}mm")

        # Konvertiere Loop zu LWPOLYLINE
        # max_sagitta kontrolliert die Auflösung von Bögen, wenn wir sie flach machen müssten.
        # Aber lwpolyline_from_chain behält Bögen (Bulges) bei, wenn möglich.
        polyline = es.lwpolyline_from_chain(loop, dxfattribs=poly_attribs)
        polyline.close(True)
        new_msp.add_entity(polyline)

    # B) Offene Ketten analysieren
    for chain in open_chains:
        # Prüfen, ob Start und Ende nah beieinander sind (Lücke <= gap_tol)
        # find_all_open_chains liefert Ketten, die NICHT geometrisch geschlossen sind (laut gap_tol im Deposit)
        # Aber Moment: Wenn sie im Deposit schon < gap_tol wären, hätte find_all_loops sie gefunden!
        # D.h. open_chains sind per Definition > gap_tol auseinander?
        # NEIN. find_all_loops sucht nach topologisch geschlossenen Kreisen im Graphen.
        # Die Lückentoleranz ist im Deposit definiert.

        # Wir schauen uns Start und Ende der Kette an.
        start_pt = chain[0].start
        end_pt = chain[-1].end

        dist = start_pt.distance(end_pt)

        is_closed_now = False

        if dist <= gap_tol:
            # Lücke schließen!
            is_closed_now = True
            closed_gaps_count += 1

            # Marker setzen an der Lücke (Mittelpunkt)
            mid_gap = start_pt.lerp(end_pt, 0.5)
            new_msp.add_circle(mid_gap, radius=gap_tol/2.0, dxfattribs={"layer": marker_layer, "color": colors.MAGENTA})
            # Optional: Kleines Kreuz oder Text
            # new_msp.add_point(mid_gap, dxfattribs={"layer": marker_layer})

            print(f"  -> Lücke geschlossen bei {mid_gap:.2f}, Abstand: {dist:.4f}mm")

        # Polylinie schreiben
        polyline = es.lwpolyline_from_chain(chain, dxfattribs=poly_attribs)
        if is_closed_now:
            polyline.close(True) # Schließt das letzte Segment automatisch gerade
        else:
            print(f"  -> Kette bleibt offen. Endpunkte-Abstand: {dist:.4f}mm (Start: {start_pt}, Ende: {end_pt})")

        new_msp.add_entity(polyline)

    # Speichern
    new_doc.saveas(output_file)
    print(f"--- Fertig. Datei gespeichert als: {output_file} ---")
    print(f"Statistik:")
    print(f"  - Geschlossene Loops: {len(loops)}")
    print(f"  - Offene Ketten verarbeitet: {len(open_chains)}")
    print(f"  - Davon nachträglich geschlossen: {closed_gaps_count}")


if __name__ == "__main__":
    # Testlauf mit default Parametern
    cleanup_dxf("dirty_input.dxf", "clean_output.dxf", gap_tol=1.0)

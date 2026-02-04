import ezdxf
from ezdxf import colors
from ezdxf import edgeminer as em
from ezdxf import edgesmith as es
from typing import List, Tuple
import sys
import argparse
import os

def cleanup_dxf(input_file: str, output_file: str,
                gap_tol: float = 1.0,
                target_layer: str = "SCHNITT_CONTUR",
                marker_layer: str = "MARKER_WARNING"):

    print(f"--- Starte Reinigung von {input_file} ---")

    if not os.path.exists(input_file):
        print(f"Fehler: Datei '{input_file}' nicht gefunden.")
        sys.exit(1)

    try:
        doc = ezdxf.readfile(input_file)
    except Exception as e:
        print(f"Fehler beim Lesen der Datei: {e}")
        sys.exit(1)

    msp = doc.modelspace()

    # ---------------------------------------------------------
    # Schritt 1: Unnötige Entities löschen
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
    # Schritt 2: Geometrie filtern & Vorbereiten
    # ---------------------------------------------------------
    candidates = []

    # a) Polylinien: Auch geschlossene müssen berücksichtigt werden.
    # Wir zerlegen sie in ihre Bestandteile (virtuelle Entities), damit Edgeminer
    # den Graphen korrekt bauen kann.
    all_polylines = msp.query('LWPOLYLINE POLYLINE')
    for pl in all_polylines:
        if pl.is_closed:
            candidates.extend(pl.virtual_entities())
        else:
            candidates.append(pl)

    # b) Andere lineare Entities
    candidates.extend(msp.query('LINE ARC SPLINE ELLIPSE'))

    # Wir nutzen eine SEHR kleine Toleranz für den Graphen-Aufbau (Topology).
    # Das verhindert, dass eng beieinander liegende Ringe (z.B. 0.8mm Abstand) verschmelzen.
    GRAPH_TOLERANCE = 0.001 # 1 Mikrometer

    input_edges = list(es.edges_from_entities_2d(candidates, gap_tol=GRAPH_TOLERANCE))
    print(f"Gefundene Geometrie-Kanten (inkl. zerlegter Polylinien): {len(input_edges)}")

    # ---------------------------------------------------------
    # Sonderfall: Kreise (CIRCLE)
    # ---------------------------------------------------------
    circles = msp.query('CIRCLE')
    print(f"Gefundene Kreise (Löcher): {len(circles)}")

    # ---------------------------------------------------------
    # Schritt 3: Deduplizierung (Deaktiviert)
    # ---------------------------------------------------------
    deposit = em.Deposit(input_edges, gap_tol=GRAPH_TOLERANCE)

    # Duplikate filtern
    # ACHTUNG: em.filter_coincident_edges nutzt standardmäßig nur Start/Endpunkt-Vergleich.
    # Bei Arcs/Splines kann das zu Fehlern führen (unterschiedliche Kurven mit gleichen Endpunkten).
    # Wir deaktivieren es sicherheitshalber, um Geometrieverlust bei Ringen zu vermeiden.
    # unique_edges = em.filter_coincident_edges(deposit)
    unique_edges = deposit.edges
    print(f"Kanten nach Deduplizierung (deaktiviert): {len(unique_edges)}")

    # Neues Deposit mit bereinigten Kanten
    clean_deposit = em.Deposit(unique_edges, gap_tol=GRAPH_TOLERANCE)

    # ---------------------------------------------------------
    # Schritt 4: Kettenbildung
    # ---------------------------------------------------------

    # A) Geschlossene Loops (Innerhalb 1µm Toleranz)
    loops = list(em.find_all_loops(clean_deposit))

    # B) Offene Ketten
    open_chains = list(em.find_all_open_chains(clean_deposit))

    print(f"Gefundene geschlossene Konturen (perfekt): {len(loops)}")
    print(f"Gefundene offene Ketten: {len(open_chains)}")

    # ---------------------------------------------------------
    # Schritt 5: Ausgabe & Schließen von Lücken
    # ---------------------------------------------------------
    new_doc = ezdxf.new("R2010")
    new_msp = new_doc.modelspace()

    if target_layer not in new_doc.layers:
        new_doc.layers.add(target_layer, color=colors.WHITE)
    if marker_layer not in new_doc.layers:
        new_doc.layers.add(marker_layer, color=colors.MAGENTA)

    poly_attribs = {"layer": target_layer}
    closed_gaps_count = 0

    # 1. Kreise schreiben
    for circle in circles:
        try:
             center = circle.dxf.center
             radius = circle.dxf.radius
             points = [
                 (center.x - radius, center.y, 1.0),
                 (center.x + radius, center.y, 1.0)
             ]
             pl = new_msp.add_lwpolyline(points, format="xyb", dxfattribs=poly_attribs)
             pl.close(True)
        except Exception as e:
            print(f"Fehler beim Konvertieren von Kreis: {e}")

    # 2. Perfekte Loops schreiben
    for loop in loops:
        polyline = es.lwpolyline_from_chain(loop, dxfattribs=poly_attribs)
        polyline.close(True)
        new_msp.add_entity(polyline)

    # 3. Offene Ketten prüfen und ggf. schließen
    for chain in open_chains:
        start_pt = chain[0].start
        end_pt = chain[-1].end
        dist = start_pt.distance(end_pt)

        is_closed_now = False

        # Hier wenden wir die GROSSE Toleranz an (User Input, z.B. 1.0mm)
        # Wenn Start und Ende nah genug sind, schließen wir den Loop.
        if dist <= gap_tol:
            is_closed_now = True
            closed_gaps_count += 1

            mid_gap = start_pt.lerp(end_pt, 0.5)
            new_msp.add_circle(mid_gap, radius=gap_tol/2.0, dxfattribs={"layer": marker_layer, "color": colors.MAGENTA})
            print(f"  -> Lücke geschlossen bei {mid_gap}, Abstand: {dist:.4f}mm")

        polyline = es.lwpolyline_from_chain(chain, dxfattribs=poly_attribs)
        if is_closed_now:
            polyline.close(True)
        else:
            print(f"  -> Kette bleibt offen. Endpunkte-Abstand: {dist:.4f}mm")

        new_msp.add_entity(polyline)

    new_doc.saveas(output_file)
    print(f"--- Fertig. Datei gespeichert als: {output_file} ---")
    print(f"Statistik:")
    print(f"  - Geschlossene Loops (Original): {len(loops)}")
    print(f"  - Gefundene Kreise: {len(circles)}")
    print(f"  - Offene Ketten verarbeitet: {len(open_chains)}")
    print(f"  - Davon nachträglich geschlossen (Lücke < {gap_tol}mm): {closed_gaps_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DXF Cleaner für Laserschneiden")
    parser.add_argument("input", nargs='?', default="dirty_input.dxf", help="Eingabe DXF Datei")
    parser.add_argument("output", nargs='?', default="clean_output.dxf", help="Ausgabe DXF Datei")
    parser.add_argument("--gap", type=float, default=1.0, help="Maximale Lückengröße die geschlossen wird (Default: 1.0mm)")
    parser.add_argument("--layer", type=str, default="SCHNITT_CONTUR", help="Ziel-Layer für Konturen")

    args = parser.parse_args()

    cleanup_dxf(args.input, args.output, gap_tol=args.gap, target_layer=args.layer)

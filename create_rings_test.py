import ezdxf

def create_rings_test(filename):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 1. Konzentrische KREISE (CIRCLE Entities)
    # Radien: 10, 11, 12. Abstand 1mm.
    # Wenn gap_tol=1.0mm ist, könnte hier was passieren, wenn wir sie falsch behandeln?
    msp.add_circle((0, 0), radius=10, dxfattribs={"layer": "OBJECTS"})
    msp.add_circle((0, 0), radius=11, dxfattribs={"layer": "OBJECTS"})
    msp.add_circle((0, 0), radius=12, dxfattribs={"layer": "OBJECTS"})

    # 2. Konzentrische Ringe aus BÖGEN (ARCs) -> Hier greift Edgeminer!
    # Ein Kreis aus zwei Halbkreisen (ARCs) nachgebaut.
    def add_arc_circle(center, radius):
        cx, cy = center
        # Halbkreis 1
        msp.add_arc(center, radius, 0, 180, dxfattribs={"layer": "ARCS"})
        # Halbkreis 2
        msp.add_arc(center, radius, 180, 360, dxfattribs={"layer": "ARCS"})

    # Radien: 30, 30.8, 32.
    # Abstand 0.8mm (kleiner als default Gap 1.0mm!)
    # Hier besteht die Gefahr, dass der innere Ring (30.8) an den äußeren (30.0) "gesnappt" wird?
    add_arc_circle((50, 0), 30.0)
    add_arc_circle((50, 0), 30.8) # Abstand 0.8 zu Ring 1
    add_arc_circle((50, 0), 32.0)

    # 3. Konzentrische Rechtecke (Polylinien)
    # Abstand 0.5mm
    msp.add_lwpolyline([(80, 0), (90, 0), (90, 10), (80, 10)], close=True) # Box 10x10
    msp.add_lwpolyline([(79.5, -0.5), (90.5, -0.5), (90.5, 10.5), (79.5, 10.5)], close=True) # Box 11x11 (Abstand 0.5)

    doc.saveas(filename)
    print(f"Created {filename}")

if __name__ == "__main__":
    create_rings_test("rings_test.dxf")

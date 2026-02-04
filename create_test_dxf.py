import ezdxf
from ezdxf import colors

def create_test_dxf(filename):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 1. Offene Kontur (Lücke < 1.0mm) - Sollte geschlossen werden
    # Ein Rechteck 10x10 bei (0,0), aber die letzte Seite fehlt ein Stück
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=False, dxfattribs={"layer": "OBJECTS"})
    # Lücke von (0, 10) nach (0, 0.5) -> Abstand 0.5mm
    msp.add_line((0, 10), (0, 0.5), dxfattribs={"layer": "OBJECTS"})

    # 2. Offene Kontur (Lücke > 1.0mm) - Sollte OFFEN bleiben
    # Ein Rechteck bei (20, 0)
    msp.add_lwpolyline([(20, 0), (30, 0), (30, 10), (20, 10)], close=False, dxfattribs={"layer": "OBJECTS"})
    # Lücke von (20, 10) nach (20, 1.5) -> Abstand 1.5mm
    msp.add_line((20, 10), (20, 1.5), dxfattribs={"layer": "OBJECTS"})

    # 3. Doppelte Linien
    # Eine Linie bei (40, 0) bis (50, 0)
    msp.add_line((40, 0), (50, 0), dxfattribs={"layer": "OBJECTS", "color": colors.RED})
    # Eine exakte Kopie darüber
    msp.add_line((40, 0), (50, 0), dxfattribs={"layer": "OBJECTS", "color": colors.BLUE})

    # 4. Unnötiger Text und Bemaßung
    msp.add_text("Kundenname: Müller", dxfattribs={"height": 0.5, "insert": (0, -2), "layer": "TEXT"})
    msp.add_text("Material: 1.4301", dxfattribs={"height": 0.5, "insert": (0, -3), "layer": "TEXT"})

    # Dimension (Linear)
    dim = msp.add_linear_dim(base=(0, -5), p1=(0, 0), p2=(10, 0), dxfattribs={"layer": "DIMENSIONS"})
    dim.render()

    # 5. Kreis (geschlossen, sollte erhalten bleiben)
    msp.add_circle((60, 5), radius=2, dxfattribs={"layer": "OBJECTS"})

    doc.saveas(filename)
    print(f"Test file created: {filename}")

if __name__ == "__main__":
    create_test_dxf("dirty_input.dxf")

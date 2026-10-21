"""Build the formal context from config.CONTEXT and draw its concept lattice.

Run:  python lattice.py   (prints each concept, saves out/lattice.png)
"""

from pathlib import Path

from concepts import Context

from config import CONTEXT


def mk_formal_context(context):
    """concepts.Context from a {object: 0/1 row} dict like CONTEXT."""
    objects = list(context)
    n_att = len(context[objects[0]])
    properties = [f"m{j}" for j in range(n_att)]

    # fromdict() wants attribute positions, not 0/1: [1, 1, 0] -> [0, 1]
    rows_as_positions = []
    for obj in objects:
        row = context[obj]
        positions = [j for j, value in enumerate(row) if value == 1]
        rows_as_positions.append(positions)

    return Context.fromdict({
        "objects": objects,
        "properties": properties,
        "context": rows_as_positions,
    })


def draw_lattice(lattice):
    """Save a picture of the lattice to out/lattice.png.

    Graphviz settings: https://graphviz.org/doc/info/attrs.html
    """
    dot = lattice.graphviz(
        make_object_label=lambda objs: ", ".join(objs),
        make_property_label=lambda props: ", ".join(props),
    )

    dot.node_attr.update(width="0.12",          # inches
                         fillcolor="steelblue",
                         color="steelblue")
    dot.edge_attr.update(color="gray50",
                         fontsize="10",
                         fontname="Helvetica")
    dot.graph_attr.update(nodesep="0.3", splines="line")

    # out/ is at the project root, next to demo/
    out_dir = Path(__file__).resolve().parent.parent / "out"
    # cleanup=True deletes graphviz's source file and keeps only the PNG
    path = dot.render(filename="lattice", directory=out_dir,
                      format="png", cleanup=True)
    print(f"saved to {path}")


if __name__ == "__main__":
    fc = mk_formal_context(CONTEXT)

    # extent = objects, intent = their shared attributes
    for extent, intent in fc.lattice:
        print(extent, intent)

    draw_lattice(fc.lattice)

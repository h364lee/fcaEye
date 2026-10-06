from pathlib import Path

from concepts import Context

from context import CONTEXT


def mk_formal_context(context):
    """
    1. Takes CONTEXT
    2. concepts.Context.fromdict() does not take 0/1 rows; 
    it takes the positions of the attributes the object has. 
    Each row is converted as such: e.g. [1, 1, 1, 0, 0, 0] -> [0, 1, 2].
    3. Returns the context object.
    """
    objects = list(context)
    n_att = len(context[objects[0]])
    # Attribute labels follow the column position, so m0 is column 0.
    properties = [f"m{j}" for j in range(n_att)]

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

    dot.node_attr.update(width="0.12",          # node size
                         fillcolor="steelblue",
                         color="steelblue")
    dot.edge_attr.update(color="gray50",        # edges and their labels
                         fontsize="10",
                         fontname="Helvetica")
    # nodesep: horizontal gap between nodes
    dot.graph_attr.update(nodesep="0.3", splines="line")

    # out/ sits at the project root, next to demo/
    out_dir = Path(__file__).resolve().parent.parent / "out"
    # cleanup=True deletes graphviz's text file and keeps only the PNG
    path = dot.render(filename="lattice", directory=out_dir,
                      format="png", cleanup=True)
    print(f"saved to {path}")


if __name__ == "__main__":
    fc = mk_formal_context(CONTEXT)

    # Each formal concept: (extent, intent) = (its objects, their shared attributes)
    for extent, intent in fc.lattice:
        print(extent, intent)

    draw_lattice(fc.lattice)

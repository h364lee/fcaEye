from concepts import Context

# Construct a context from dict
n_obj, n_att = 8, 6

d = {
    'objects': [f'g{i}' for i in range(n_obj)],
    'properties': [f'm{j}' for j in range(n_att)],

    'context': [
        [0, 1, 2],
        [0, 2, 4], 
        [0, 1, 3],
        [0, 3, 5],
        [3, 4, 5],
        [1, 3, 5],
        [2, 4, 5], 
        [1, 2, 4],
    ]
}

c = Context.fromdict(d)

for extent, intent in c.lattice:
    print(extent, intent)


# Lattice graph
# see graphviz settings at https://graphviz.org/doc/info/attrs.html
L = c.lattice

dot = L.graphviz(
    make_object_label=lambda objs: ', '.join(objs),
    make_property_label=lambda props: ', '.join(props),
)

# graph defaults
dot.node_attr.update(width='0.12',              #nodes
                     fillcolor='steelblue', 
                     color='steelblue')    
dot.edge_attr.update(color='gray50',            #edges and label
                     fontsize='10', 
                     fontname='Helvetica')       
dot.graph_attr.update(nodesep='0.3', splines='line')            #whole-graph settings (nodesep is the horizontal gap between nodes)          

# highlight one concept, x/y
x, y = L['m0',], L['m2',]
dot.node(f'c{x.index}', fillcolor='orange', color='orange', width='0.2')    
dot.node(f'c{y.index}', fillcolor='red', color='red', width='0.2')

# draw. cleanup=True deletes the text file and keeps the image only
dot.render(filename='lattice_custom', directory='out', format='png', cleanup=True, view=True)
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib import cm
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages

def plot_routes(f_routes, G, objective_function_value, R, P, D, distances):

    """ Function: plot routes"""

    graph_title = 'Routes graph'
    example_name = '15_(8P-7D)_8V'
    example_name = 'obj_deviation_' + example_name
    pp = PdfPages(example_name + '.pdf')
    nodes_colors = []
    for i in G.nodes:
        if i in [req.origin.gps_coordinates.id for req in D]:
            nodes_colors.append("#ADFABC")

        elif i in [req.destination.gps_coordinates.id for req in P]:
            nodes_colors.append("#F26326")
        else:
            nodes_colors.append("yellow")


    edge_labels = dict([((U, V), data['length']) for U, V, data in G.edges(data=True)])

    #colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'Aqua']
    nb_colors = len(f_routes)
    colors = cm.rainbow(np.linspace(0, 1, nb_colors))
    paths = []
    # f_routes = get_routes_dict()
    for i in f_routes.keys():
        paths.append({'route': [(f_routes[i][j], f_routes[i][j + 1]) for j in range(len(f_routes[i]) - 1)],
                      'color': colors[i]})

    # pos = nx.spring_layout(G, seed=3)
    #pos = {i: j for i, j in zip(G.nodes, coordinates)}
    pos = {}
    for node in G.nodes(data=True):
         pos[node[0]] = node[1]['pos']


    nx.draw_networkx_nodes(G, pos, cmap=plt.get_cmap('jet'), node_color=nodes_colors)
    nx.draw_networkx_labels(G, pos)

    for path in paths:
        path_edge_labels = {}
        for (u, v) in path['route']:
            path_edge_labels[(u, v)] = distances[u][v]

        nx.draw_networkx_edges(G, pos, edgelist=path['route'], edge_color=path['color'], arrows=True)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=path_edge_labels)

    plt.gca().set_title(graph_title)

    patches = []
    for i in range(len(paths)):
        patches.append(mpatches.Patch(color=paths[i]['color'], linewidth=None, label='vehicle_' + str(i)))

    plt.legend(handles=patches, loc='best')
    plt.savefig(pp, format='pdf')
    plt.show()
    plt.axis([0, 15, 0, 15])
    comments = "total cost (Objective): " + str(-objective_function_value)
    comments += "\ntotal deviation : " + str(-objective_function_value) + " %"
    comments += "\nTravel time in this solution // Travel time in direct route // Deviation // Difference\n"

    for f_rt in f_routes.keys():
        comments += str('\n------------------------------------------------\n==> vehicle_' + str(f_rt) + '\n')
        for f_i in f_routes[f_rt]:
            if f_i != 0:
                travel_time_solution = R[f_i]
                travel_time_direct_route = (distances[0][f_i] if f_i in D else distances[f_i][0])
                f_deviation = (travel_time_solution / travel_time_direct_route - 1) * 100
                f_difference = travel_time_solution - travel_time_direct_route
                comments += str('- client_' + str(f_i) + ' ' + ('Pickup ' if f_i in P else 'Delivery ') + ': '
                                + str(travel_time_solution.__round__(3)) + '  //  ' + str(travel_time_direct_route))
                comments += str('  //  +' + str(f_deviation.__round__(1)) + '%  //  ' + str(f_difference.__round__(3))
                                + '\n')

                if comments.count('\n') > 26:
                    plt.text(0, 15, comments, fontsize=9, ha='left', va='top', wrap=True)
                    plt.axis('off')
                    plt.savefig(pp, format='pdf')
                    plt.show()
                    plt.axis([0, 15, 0, 15])
                    comments = ''

    plt.text(0, 15, comments, fontsize=9, ha='left', va='top', wrap=True)
    plt.axis('off')
    plt.savefig(pp, format='pdf')
    plt.show()

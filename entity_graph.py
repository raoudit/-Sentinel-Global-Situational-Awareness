"""
entity_graph.py
Builds a simple entity relationship graph showing which countries/regions
co-occur in flagged events (a simplified version of "link analysis" used
in real intelligence-analysis tools).
"""

import networkx as nx
import random


def build_entity_graph(df, max_edges=25):
    """
    Builds a graph where nodes = countries, edges = co-occurrence relationships
    (simulated by random pairing weighted toward high-risk countries — a simple
    stand-in for real co-mention/link analysis).
    """
    G = nx.Graph()
    countries = df["country"].unique().tolist()

    for c in countries:
        count = len(df[df["country"] == c])
        G.add_node(c, weight=count)

    # Create edges between countries that share an event_type (simple relationship rule)
    edges_added = 0
    event_types = df["event_type"].unique()
    for etype in event_types:
        subset = df[df["event_type"] == etype]["country"].unique().tolist()
        for i in range(len(subset)):
            for j in range(i + 1, len(subset)):
                if edges_added >= max_edges:
                    break
                if subset[i] != subset[j]:
                    G.add_edge(subset[i], subset[j], relation=etype)
                    edges_added += 1

    return G


def graph_to_plotly_elements(G):
    """Converts a networkx graph into node/edge coordinate lists for Plotly rendering."""
    pos = nx.spring_layout(G, seed=42, k=0.8)

    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x, node_y, node_text, node_size = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_size.append(15 + G.nodes[node].get("weight", 1) * 4)

    return edge_x, edge_y, node_x, node_y, node_text, node_size

import os
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from classes.sqlparser import ParserSQL


def gerar_grafo(sql_query, nome_arquivo="grafo.png"):
    """
    Gera e salva um grafo simples (png) a partir de uma query SQL.
    """
    parser = ParserSQL(sql_query)
    parser.parse()
    comp = parser.components

    G = nx.DiGraph()

    from_node = f"FROM: {comp.get('from', '')}"
    G.add_node(from_node)

    for i, join in enumerate(comp.get("joins", []), 1):
        jnode = f"JOIN{i}: {join.get('table', '')}"
        G.add_node(jnode)
        G.add_edge(from_node, jnode, label=f"ON {join.get('on', '')}")
        from_node = jnode

    if comp.get("where"):
        where_node = f"WHERE: {comp['where']}"
        G.add_node(where_node)
        G.add_edge(from_node, where_node)
        last_node = where_node
    else:
        last_node = from_node

    select_node = f"SELECT: {comp.get('select', '*')}"
    G.add_node(select_node)
    G.add_edge(last_node, select_node)

    pos = nx.shell_layout(G)
    plt.figure(figsize=(9, 5))
    nx.draw(G, pos, with_labels=True, node_size=2500, node_color="#A3C4BC", font_size=8, arrows=True)
    edge_labels = nx.get_edge_attributes(G, 'label')
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)
    plt.title("Grafo da consulta SQL")
    plt.tight_layout()

    os.makedirs("grafos", exist_ok=True)
    caminho = os.path.join("grafos", nome_arquivo)
    plt.savefig(caminho, dpi=150)
    plt.close()

    print(f"[✔] Grafo gerado: {caminho}")
    return caminho

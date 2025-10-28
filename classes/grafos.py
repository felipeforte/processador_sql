import os
import re
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from classes.sqlparser import ParserSQL


def _construir_grafo_literal(comp, G):
    """Grafo 1: Literal – ordem exata da query SQL."""
    from_node = f"FROM: {comp.get('from', '')}"
    G.add_node(from_node)

    current = from_node
    for i, join in enumerate(comp.get("joins", []), 1):
        jnode = f"JOIN{i}: {join.get('table', '')}"
        G.add_node(jnode)
        G.add_edge(current, jnode, label=f"ON {join.get('on', '')}")
        current = jnode

    if comp.get("where"):
        where_node = f"WHERE: {comp['where']}"
        G.add_node(where_node)
        G.add_edge(current, where_node)
        current = where_node

    select_node = f"SELECT: {comp.get('select', '*')}"
    G.add_node(select_node)
    G.add_edge(current, select_node)


def _construir_grafo_reducao_tuplas(parser, G):
    """Grafo 2: Heurística – Redução de Tuplas (seleções precoces)."""
    comp = parser.components
    tabelas = []

    # Extrair tabelas com alias
    from_part = comp['from']
    if ' ' in from_part:
        tab, alias = from_part.split(' ', 1)
        tabelas.append((tab, alias.strip()))
    else:
        tabelas.append((from_part, from_part))

    for j in comp['joins']:
        jp = j['table']
        if ' ' in jp:
            t, a = jp.split(' ', 1)
            tabelas.append((t, a.strip()))
        else:
            tabelas.append((jp, jp))

    alias_para_tabela = {alias: nome for nome, alias in tabelas}

    # Separar seleções por tabela
    selecoes = {alias: [] for _, alias in tabelas}
    multi = []
    if comp['where']:
        conds = parser._quebrar_and(comp['where'])
        for c in conds:
            tabs = parser._extrair_tabelas_da_condicao(c, alias_para_tabela)
            if len(tabs) == 1:
                selecoes[list(tabs)[0]].append(c)
            else:
                multi.append(c)

    # Criar nós
    nos_tabela = {}
    for nome, alias in tabelas:
        base = nome
        if alias != nome:
            base = f"ρ: {alias}←{nome}"
        if selecoes[alias]:
            sigma = f"σ: {' ∧ '.join(selecoes[alias])}"
            G.add_node(base)
            G.add_node(sigma)
            G.add_edge(base, sigma)
            nos_tabela[alias] = sigma
        else:
            G.add_node(base)
            nos_tabela[alias] = base

    # Junções
    aliases = [alias for _, alias in tabelas]
    current = nos_tabela[aliases[0]]

    for i in range(1, len(aliases)):
        alias_atual = aliases[i]
        join_cond = comp['joins'][i - 1]['on']
        join_node = f"⨝: {join_cond}"
        G.add_node(join_node)
        G.add_edge(current, join_node)
        G.add_edge(nos_tabela[alias_atual], join_node)
        current = join_node

    # Condições multi-tabela
    if multi:
        sigma_multi = f"σ: {' ∧ '.join(multi)}"
        G.add_node(sigma_multi)
        G.add_edge(current, sigma_multi)
        current = sigma_multi

    # SELECT
    select_node = f"SELECT: {comp['select']}"
    G.add_node(select_node)
    G.add_edge(current, select_node)


def _construir_grafo_reducao_atributos(parser, G):
    """Grafo 3: Heurística – Redução de Atributos (projeções precoces)."""
    comp = parser.components
    tabelas = []

    from_part = comp['from']
    if ' ' in from_part:
        tab, alias = from_part.split(' ', 1)
        tabelas.append((tab, alias.strip()))
    else:
        tabelas.append((from_part, from_part))

    for j in comp['joins']:
        jp = j['table']
        if ' ' in jp:
            t, a = jp.split(' ', 1)
            tabelas.append((t, a.strip()))
        else:
            tabelas.append((jp, jp))

    alias_para_tabela = {alias: nome for nome, alias in tabelas}

    # Coletar atributos usados
    atributos_usados = set()
    if comp['select'] != '*':
        for a in comp['select'].split(','):
            atributos_usados.add(a.strip())

    # Condições
    conds = []
    if comp['where']:
        conds.extend(parser._quebrar_and(comp['where']))
    for j in comp['joins']:
        conds.append(j['on'])

    for c in conds:
        ids = re.findall(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\b', c)
        for id_ in ids:
            if '.' in id_:
                atributos_usados.add(id_)

    # Mapear atributos por alias
    attrs_por_alias = {alias: set() for _, alias in tabelas}
    for attr in atributos_usados:
        if '.' in attr:
            pre, col = attr.split('.', 1)
            if pre in attrs_por_alias:
                attrs_por_alias[pre].add(col)
            else:
                for al, nome in alias_para_tabela.items():
                    if nome == pre:
                        attrs_por_alias[al].add(col)
                        break

    # Criar nós com projeção
    nos_tabela = {}
    for nome, alias in tabelas:
        base = nome
        if alias != nome:
            base = f"ρ: {alias}←{nome}"
        G.add_node(base)

        attrs = attrs_por_alias[alias]
        if attrs:
            pi = f"π: {', '.join(sorted(attrs))}"
            G.add_node(pi)
            G.add_edge(base, pi)
            nos_tabela[alias] = pi
        else:
            nos_tabela[alias] = base

    # Junções
    aliases = [alias for _, alias in tabelas]
    current = nos_tabela[aliases[0]]

    for i in range(1, len(aliases)):
        alias_atual = aliases[i]
        join_cond = comp['joins'][i - 1]['on']
        join_node = f"⨝: {join_cond}"
        G.add_node(join_node)
        G.add_edge(current, join_node)
        G.add_edge(nos_tabela[alias_atual], join_node)
        current = join_node

    # WHERE multi-tabela (se houver)
    selecoes = {alias: [] for _, alias in tabelas}
    multi = []
    if comp['where']:
        conds_w = parser._quebrar_and(comp['where'])
        for c in conds_w:
            tabs = parser._extrair_tabelas_da_condicao(c, alias_para_tabela)
            if len(tabs) == 1:
                # Já foi aplicado antes da projeção? Não neste grafo.
                # Para simplicidade, ignoramos σ aqui (foco é π)
                pass
            else:
                multi.append(c)

    if multi:
        sigma_multi = f"σ: {' ∧ '.join(multi)}"
        G.add_node(sigma_multi)
        G.add_edge(current, sigma_multi)
        current = sigma_multi

    # SELECT final
    select_node = f"SELECT: {comp['select']}"
    G.add_node(select_node)
    G.add_edge(current, select_node)


def gerar_grafos_otimizados(sql_query, base_nome="query"):
    """
    Gera três grafos:
      1. Literal
      2. Redução de Tuplas (seleções precoces)
      3. Redução de Atributos (projeções precoces)
    """
    parser = ParserSQL(sql_query)
    if not parser.eh_valido():
        print("[!] Consulta inválida – nenhum grafo gerado.")
        return

    comp = parser.components

    # 1. Grafo Literal
    G1 = nx.DiGraph()
    _construir_grafo_literal(comp, G1)
    _salvar_grafo(G1, f"{base_nome}_literal.png", "Grafo Literal")

    # 2. Grafo Redução de Tuplas
    G2 = nx.DiGraph()
    _construir_grafo_reducao_tuplas(parser, G2)
    _salvar_grafo(G2, f"{base_nome}_tuplas.png", "Heurística: Redução de Tuplas")

    # 3. Grafo Redução de Atributos
    G3 = nx.DiGraph()
    _construir_grafo_reducao_atributos(parser, G3)
    _salvar_grafo(G3, f"{base_nome}_atributos.png", "Heurística: Redução de Atributos")


def _salvar_grafo(G, nome_arquivo, titulo):
    pos = nx.spring_layout(G, seed=42)  # layout mais estável que shell
    plt.figure(figsize=(10, 6))
    nx.draw(
        G, pos,
        with_labels=True,
        node_size=2200,
        node_color="#A3C4BC",
        font_size=9,
        arrows=True,
        edge_color="gray"
    )
    edge_labels = nx.get_edge_attributes(G, 'label')
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    plt.title(titulo)
    plt.tight_layout()

    os.makedirs("grafos", exist_ok=True)
    caminho = os.path.join("grafos", nome_arquivo)
    plt.savefig(caminho, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[✔] {titulo} salvo: {caminho}")
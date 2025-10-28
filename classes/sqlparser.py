import re

class ParserSQL:
    def __init__(self, sql_query: str):
        self.sql_query = sql_query.strip()
        self.parsed = False
        self.valid = False
        self.components = {
            'select': None,
            'from': None,       # "tabela" ou "tabela alias"
            'joins': [],        # lista de {'table': 'tabela [alias]', 'on': 'condição'}
            'where': None
        }

    def parse(self):
        """Parse simples para SELECT, FROM, múltiplos INNER JOIN e WHERE."""
        try:
            # Cabeçalho: SELECT ... FROM ...
            head_pat = r"""
                ^\s*SELECT\s+(?P<select>.+?)\s+
                FROM\s+(?P<from>\w+(?:\s+(?:AS\s+)?\w+)?)
                (?=\s+(?:INNER\s+JOIN|WHERE|$))
                \s*(?P<rest>.*)$
                """

            m = re.search(head_pat, self.sql_query, re.IGNORECASE | re.VERBOSE | re.DOTALL)
            if not m:
                self.valid = False
                return False

            self.components['select'] = m.group('select').strip()
            self.components['from']   = m.group('from').strip()

            # Resto: zero ou mais INNER JOINs seguidos
            rest = m.group('rest') or ''
            joins = []

            join_pat = re.compile(r"""
                ^\s*INNER\s+JOIN\s+
                (?P<table>\w+(?:\s+\w+)?)\s+          # tabela OU "tabela alias"
                ON\s+(?P<cond>.+?)                    # condição do ON
                (?=\s*(?:INNER\s+JOIN|WHERE|$))       # até o próximo JOIN/WHERE/fim
            """, re.IGNORECASE | re.VERBOSE | re.DOTALL)

            while True:
                mjoin = join_pat.search(rest)
                if not mjoin or mjoin.start() != 0:    # precisa estar logo no início (descontando espaços)
                    break

                table  = mjoin.group('table').strip()
                cond   = mjoin.group('cond').strip()

                if not self._validar_condicao(cond):
                    self.valid = False
                    return False

                joins.append({'table': table, 'on': cond})
                rest = rest[mjoin.end():]              # consome esse JOIN e continua

            # WHERE (se sobrou algo em 'rest', precisa ser só WHERE ...)
            mwhere = re.match(r"^\s*(?:WHERE\s+(?P<where>.+))?\s*$", rest, re.IGNORECASE | re.DOTALL)
            if not mwhere:
                self.valid = False
                return False

            where = (mwhere.group('where') or '').strip()
            if where:
                if not self._validar_condicao(where):
                    self.valid = False
                    return False
                self.components['where'] = where

            self.components['joins'] = joins
            self.valid = True
            self.parsed = True
            return True

        except Exception:
            self.valid = False
            return False

    # Validações auxiliares

    def _validar_condicao(self, cond):
        # Rejeita operadores não permitidos explicitamente
        proibidos = [r'\bOR\b', r'\bNOT\b', r'~~', r'~', r'\bLIKE\b', r'\bIS\b', r'\bNULL\b']
        for padrao in proibidos:
            if re.search(padrao, cond, re.IGNORECASE):
                return False

        # Depois, aplicar a validação estrutural
        valid_pattern = r"""
            ^(?:\s*
                (?:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?   # coluna ou tabela.coluna
                |'[^']*'                            # string
                |\d+(?:\.\d+)?                      # número
                |<=|>=|<>|=|<|>                     # operadores
                |\(|\)                              # parênteses
                |AND                                # AND permitido
                )
            \s*)+$"""
        if not re.match(valid_pattern, cond, re.IGNORECASE | re.VERBOSE):
            return False
        return self._checar_parenteses(cond)

    def _checar_parenteses(self, text):
        count = 0
        for ch in text:
            if ch == '(':
                count += 1
            elif ch == ')':
                count -= 1
                if count < 0:
                    return False
        return count == 0

    # Acesso/Exibição

    def eh_valido(self):
        if not self.parsed:
            self.parse()
        return self.valid

    def get_components(self):
        if not self.parsed:
            self.parse()
        return self.components if self.valid else None

    # Conversão p/ Álgebra Relacional 

    def to_rel_algebra(self):
        """
        Converte para uma expressão de Álgebra Relacional simples:
          π_attrs( σ_where( FROM ⨝_{on1} T1 ⨝_{on2} T2 ... ) )
        Usa ρ (rename) quando houver alias.
        """
        if not self.parsed:
            self.parse()
        if not self.valid:
            return None

        def format_relation(name: str) -> str:
            parts = name.split()
            if len(parts) == 2:    # "tabela alias"
                table, alias = parts
                return f"ρ_{{{alias}←{table}}}({table})"
            return name

        def fmt_cond(c: str) -> str:
            # AND -> ∧ para ficar mais “RA-like”
            return re.sub(r"\bAND\b", "∧", c, flags=re.IGNORECASE)

        # Base: FROM
        expr = format_relation(self.components['from'])

        # ⨝ para cada JOIN
        for j in self.components['joins']:
            right = format_relation(j['table'])
            expr = f"({expr} ⨝_{{{fmt_cond(j['on'])}}} {right})"

        # σ WHERE (se houver)
        if self.components['where']:
            expr = f"σ_{{{fmt_cond(self.components['where'])}}}({expr})"

        # π SELECT (se não for *)
        select = self.components['select'].strip()
        if select != '*':
            # normaliza espaços e vírgulas
            attrs = ', '.join([s.strip() for s in select.split(',')])
            expr = f"π_{{{attrs}}}({expr})"

        return expr
    
    def otimizar_algebra_relacional(self):
        """
        Otimiza a álgebra relacional com heurísticas:
          - Push-down de seleções (σ)
          - Projeção precoce (π) com atributos necessários
          - Evita produtos cartesianos
        """
        if not self.parsed:
            self.parse()
        if not self.valid:
            return None

        # === ETAPA 1: Coletar todas as tabelas e aliases ===
        tabelas = []
        from_part = self.components['from']
        if ' ' in from_part:
            tabela_base, alias_base = from_part.split(' ', 1)
            tabelas.append((tabela_base, alias_base.strip()))
        else:
            tabelas.append((from_part, from_part))

        for join in self.components['joins']:
            jpart = join['table']
            if ' ' in jpart:
                t, a = jpart.split(' ', 1)
                tabelas.append((t, a.strip()))
            else:
                tabelas.append((jpart, jpart))

        alias_para_tabela = {alias: nome for nome, alias in tabelas}
        tabela_para_alias = {nome: alias for nome, alias in tabelas}

        # === ETAPA 2: Coletar todos os atributos usados ===
        atributos_usados = set()

        # Atributos no SELECT
        select = self.components['select'].strip()
        if select != '*':
            for attr in select.split(','):
                attr = attr.strip()
                atributos_usados.add(attr)

        # Atributos nas condições: WHERE e ON
        todas_condicoes = []
        if self.components['where']:
            todas_condicoes.extend(self._quebrar_and(self.components['where']))
        for join in self.components['joins']:
            todas_condicoes.append(join['on'])

        for cond in todas_condicoes:
            # Extrair todos os identificadores do tipo [tabela.]coluna
            ids = re.findall(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\b', cond)
            for id_ in ids:
                if '.' in id_:
                    atributos_usados.add(id_)  # ex: a.nome
                else:
                    # Coluna sem qualificação – ambígua; mantemos como está (não otimizamos)
                    # Em um sistema real, exigiria qualificação ou análise de esquema
                    pass

        # === ETAPA 3: Mapear atributos por tabela/alias ===
        atributos_por_alias = {alias: set() for _, alias in tabelas}

        for attr in atributos_usados:
            if '.' in attr:
                prefixo, coluna = attr.split('.', 1)
                if prefixo in atributos_por_alias:
                    atributos_por_alias[prefixo].add(coluna)
                else:
                    # Pode ser nome real da tabela; tentar mapear
                    for alias, nome_real in alias_para_tabela.items():
                        if nome_real == prefixo:
                            atributos_por_alias[alias].add(coluna)
                            break
            else:
                # Atributo não qualificado – não sabemos de qual tabela é.
                # Para segurança, **não aplicamos projeção** nesse caso.
                # Mas como nosso parser exige qualificação em joins, isso é raro.
                pass

        # === ETAPA 4: Analisar WHERE para seleções por tabela ===
        selecoes_por_tabela = {alias: [] for _, alias in tabelas}
        condicoes_multiplas = []

        where = self.components['where']
        if where:
            condicoes = self._quebrar_and(where)
            for cond in condicoes:
                tabelas_na_cond = self._extrair_tabelas_da_condicao(cond, alias_para_tabela)
                if len(tabelas_na_cond) == 1:
                    tabela_unica = list(tabelas_na_cond)[0]
                    selecoes_por_tabela[tabela_unica].append(cond)
                else:
                    condicoes_multiplas.append(cond)

        # === ETAPA 5: Construir expressões com σ e π precoces ===
        expressoes_tabela = {}

        for nome_real, alias in tabelas:
            expr = nome_real

            # Renomeação se necessário
            if alias != nome_real:
                expr = f"ρ_{{{alias}←{nome_real}}}({nome_real})"

            # Seleção (σ) se houver
            if selecoes_por_tabela[alias]:
                cond_join = " ∧ ".join(selecoes_por_tabela[alias])
                expr = f"σ_{{{cond_join}}}({expr})"

            # Projeção (π) com atributos necessários
            attrs_necessarios = atributos_por_alias[alias]
            if attrs_necessarios:
                # Incluir também atributos usados nas condições de junção (ON)
                # Já estão em `atributos_usados`, então ok.
                attrs_list = ', '.join(sorted(attrs_necessarios))
                expr = f"π_{{{attrs_list}}}({expr})"
            # Se não soubermos os atributos (ex: SELECT *), não aplicamos π

            expressoes_tabela[alias] = expr

        # === ETAPA 6: Montar junções na ordem original ===
        aliases_ordem = [alias for _, alias in tabelas]
        expr_atual = expressoes_tabela[aliases_ordem[0]]

        for i in range(1, len(aliases_ordem)):
            alias_atual = aliases_ordem[i]
            join_info = self.components['joins'][i - 1]
            cond_join = join_info['on']
            relacao_atual = expressoes_tabela[alias_atual]
            expr_atual = f"({expr_atual} ⨝_{{{cond_join}}} {relacao_atual})"

        # === ETAPA 7: Condições multi-tabela (WHERE) ===
        if condicoes_multiplas:
            cond_final = " ∧ ".join(condicoes_multiplas)
            expr_atual = f"σ_{{{cond_final}}}({expr_atual})"

        # === ETAPA 8: Projeção final (se SELECT não for *) ===
        if select != '*':
            attrs_finais = ', '.join([s.strip() for s in select.split(',')])
            expr_atual = f"π_{{{attrs_finais}}}({expr_atual})"

        return expr_atual

    def _quebrar_and(self, condicao: str) -> list:
        """Quebra uma condição com AND em partes, respeitando parênteses."""
        partes = []
        nivel = 0
        inicio = 0
        for i, ch in enumerate(condicao):
            if ch == '(':
                nivel += 1
            elif ch == ')':
                nivel -= 1
            elif nivel == 0 and condicao[i:i+3].upper() == 'AND':
                partes.append(condicao[inicio:i].strip())
                inicio = i + 3
        partes.append(condicao[inicio:].strip())
        return partes

    def _extrair_tabelas_da_condicao(self, condicao: str, alias_para_tabela: dict) -> set:
        """Extrai os aliases (ou nomes de tabelas) usados em uma condição."""
        # Padrão para identificadores: [tabela.]coluna
        ids = re.findall(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\b', condicao)
        tabelas_usadas = set()
        for id_ in ids:
            if '.' in id_:
                prefixo = id_.split('.')[0]
                if prefixo in alias_para_tabela:
                    tabelas_usadas.add(prefixo)
                elif prefixo in alias_para_tabela.values():
                    # Caso o nome real seja usado diretamente
                    for alias, nome in alias_para_tabela.items():
                        if nome == prefixo:
                            tabelas_usadas.add(alias)
                            break
            else:
                # Coluna sem qualificação – ambígua, consideramos todas? 
                # Para simplicidade, ignoramos (ou assumimos que não ocorre em queries válidas)
                pass
        return tabelas_usadas

    def print_components(self):
        if not self.parsed:
            self.parse()

        if not self.valid:
            print("Consulta SQL inválida!")
            return

        print("Consulta SQL válida!")
        print("Componentes:")
        print(f"  SELECT: {self.components['select']}")
        print(f"  FROM:   {self.components['from']}")
        if self.components['joins']:
            for i, j in enumerate(self.components['joins'], 1):
                print(f"  JOIN {i}: {j['table']} ON {j['on']}")
        if self.components['where']:
            print(f"  WHERE:  {self.components['where']}")

        ra_original = self.to_rel_algebra()
        ra_otimizada = self.otimizar_algebra_relacional()

        if ra_original:
            print("\nÁlgebra Relacional (Original):")
            print(f"  {ra_original}")
        if ra_otimizada:
            print("\nÁlgebra Relacional (Otimizada):")
            print(f"  {ra_otimizada}")

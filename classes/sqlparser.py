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
                FROM\s+(?P<from>\w+(?:\s+\w+)?)\s*
                (?P<rest>.*)$
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
        """
        Aceita:
          - identificadores simples ou qualificados (a.id, pedidos.cliente_id)
          - strings entre aspas simples
          - números
          - comparadores permitidos (=, >, <, <=, >=, <>)
          - parênteses
          - operador lógico AND (somente)
        """
        valid_pattern = r"""
            ^(?:\s*
                (?:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?   # id ou id.id
                  |'[^']*'                            # strings '...'
                  |\d+(?:\.\d+)?                      # números
                  |<=|>=|<>|=|<|>                     # comparadores
                  |\(|\)                              # parênteses
                  |AND                                # apenas AND
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
        ra = self.to_rel_algebra()
        if ra:
            print("Álgebra Relacional:")
            print(f"  {ra}")

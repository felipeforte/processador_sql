import re

class ParserSQL:
    def __init__(self, sql_query):
        self.sql_query = sql_query.strip()
        self.parsed = False
        self.components = {
            'select': None,
            'from': None,
            'inner_join': None,
            'where': None
        }
        self.valid = False
        
    def parse(self):
        try:
            pattern = r"""
                SELECT\s+(?P<select>.+?)\s+
                FROM\s+(?P<from>\w+)\s*
                (?:INNER\s+JOIN\s+(?P<inner_join>\w+)\s+ON\s+(?P<join_condicao>.+?)\s*)?
                (?:WHERE\s+(?P<where>.+))?
            """
            
            match = re.search(pattern, self.sql_query, re.IGNORECASE | re.VERBOSE | re.DOTALL)
            
            if not match:
                self.valid = False
                return False
                
            self.components['select'] = match.group('select')
            self.components['from'] = match.group('from')
            
            inner_join = match.group('inner_join')
            join_condicao = match.group('join_condicao')
            if inner_join and join_condicao:
                self.components['inner_join'] = f"{inner_join} ON {join_condicao}"
                if not self._validar_condicao(join_condicao):
                    self.valid = False
                    return False
            
            where_condicao = match.group('where')
            if where_condicao:
                self.components['where'] = where_condicao
                if not self._validar_condicao(where_condicao):
                    self.valid = False
                    return False
            
            self.valid = True
            self.parsed = True
            return True
            
        except Exception:
            self.valid = False
            return False
    
    def _validar_condicao(self, condicao):
        """Valida se a condição contém apenas operadores permitidos"""
        valid_pattern = r"""
            ^(?:\s*                                    # Início
            (?:                                        # Grupos de:
                \w+                                    # - Nomes de colunas/tabelas
                |'[^']*'                               # - Strings entre aspas simples
                |\d+(?:\.\d+)?                         # - Números (inteiros ou decimais)
                |<=|>=|<>|[=<>]                        # - Operadores de comparação
                |\(|\)                                 # - Parênteses
                |AND                                   # - Operador AND
            )\s*                                       # Espaços opcionais
            )+$                                        # Um ou mais grupos até o fim
        """
        
        if not re.match(valid_pattern, condicao, re.VERBOSE | re.IGNORECASE):
            return False
            
        if not self._checar_parenteses(condicao):
            return False
            
        return True
    
    def _checar_parenteses(self, text):
        """Verifica se os parênteses estão balanceados"""
        count = 0
        for char in text:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
                if count < 0:
                    return False
        return count == 0
    
    def eh_valido(self):
        return self.valid
    
    def get_components(self):
        if not self.parsed:
            self.parse()
        return self.components if self.valid else None
    
    def print_components(self):
        if not self.parsed:
            self.parse()
            
        if not self.valid:
            print("Consulta SQL inválida!")
            return
            
        print("Consulta SQL válida!")
        print("Componentes:")
        for key, value in self.components.items():
            if value:
                print(f"  {key.upper()}: {value}")
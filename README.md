# 🔍 Processador SQL - Otimizador de Consultas

Um sistema inteligente para análise, otimização e visualização de consultas SQL.

## 📋 Sobre o Projeto

Este processador SQL analisa consultas SELECT, converte-as em álgebra relacional e aplica heurísticas de otimização. O sistema gera visualizações gráficas que mostram como as consultas podem ser otimizadas para melhor performance.

## ✨ Funcionalidades

- ✅ **Parser SQL** com validação completa de sintaxe
- 🔄 **Conversão** para Álgebra Relacional (notação matemática)
- 🚀 **Otimização** automática com heurísticas clássicas:
  - Push-down de seleções (redução de tuplas)
  - Projeção precoce (redução de atributos)
- 📊 **Visualização** através de grafos direcionados
- 🎨 **Interface Web** moderna e intuitiva

## 🚀 Como Usar

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/felipeforte/processador_sql.git
cd processador_sql
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Executar a Interface Web

Para iniciar a interface web interativa:

```bash
streamlit run app.py
```

A aplicação abrirá automaticamente no seu navegador em `http://localhost:8501`

### Executar via Linha de Comando

Para processar consultas via terminal:

```bash
python main.py
```

## 📝 Operações Suportadas

### ✅ Suportado:
- `SELECT` com colunas específicas ou `*`
- `FROM` com aliases de tabelas
- `INNER JOIN` (incluindo múltiplos JOINs)
- `WHERE` com condições usando operadores:
  - Comparação: `=`, `<`, `>`, `<=`, `>=`, `<>`
  - Lógico: `AND`

### ❌ Não Suportado:
- Operadores `OR`, `NOT`
- `LIKE`, `IS NULL`, `IS NOT NULL`
- Outros tipos de JOIN (`LEFT`, `RIGHT`, `FULL`)
- Outras operações DML (`INSERT`, `UPDATE`, `DELETE`)

## 💡 Exemplos

### Consulta Simples
```sql
SELECT nome, idade FROM clientes WHERE idade > 25
```

### JOIN com Aliases
```sql
SELECT a.nome, b.data 
FROM tabela_a a 
INNER JOIN tabela_b b ON a.id = b.id 
WHERE a.status = 'ativo'
```

### Múltiplos JOINs
```sql
SELECT p.idPedido, c.Nome 
FROM Pedido p 
INNER JOIN Cliente c ON p.Cliente_idCliente = c.idCliente 
INNER JOIN Status s ON p.Status_idStatus = s.idStatus 
WHERE c.Nome = 'Joao' AND s.idStatus >= 2
```

## 🎓 Conceitos de Otimização

O sistema implementa duas heurísticas principais:

### 1. Redução de Tuplas (Push-down de Seleções)
- Aplica filtros WHERE o mais cedo possível
- Reduz o número de linhas antes das operações de JOIN
- Minimiza dados intermediários

### 2. Redução de Atributos (Projeção Precoce)
- Seleciona apenas colunas necessárias desde o início
- Reduz largura das tabelas intermediárias
- Otimiza uso de memória

## 📊 Grafos Gerados

O sistema gera três tipos de grafos para cada consulta:

1. **Grafo Literal**: Representação direta da ordem da consulta SQL
2. **Grafo com Redução de Tuplas**: Mostra aplicação de seleções precoces
3. **Grafo com Redução de Atributos**: Mostra aplicação de projeções precoces

## 🛠️ Tecnologias

- **Python 3.x**
- **Streamlit** - Interface web interativa
- **NetworkX** - Geração e manipulação de grafos
- **Matplotlib** - Visualização de grafos
- **Regex** - Parsing de SQL

## 📁 Estrutura do Projeto

```
processador_sql/
├── app.py              # Interface web Streamlit
├── main.py             # Script de linha de comando
├── requirements.txt    # Dependências
├── README.md          # Documentação
├── classes/
│   ├── __init__.py
│   ├── sqlparser.py   # Parser e otimizador SQL
│   └── grafos.py      # Gerador de grafos
└── grafos/            # Grafos gerados (criado automaticamente)
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Submeter pull requests

## 📄 Licença

Este projeto é open source e está disponível sob a licença MIT.

## 👨‍💻 Autor

Desenvolvido com ❤️ para estudos de otimização de banco de dados.

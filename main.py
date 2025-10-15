from classes import ParserSQL

queries = [
    # Consultas válidas
    "SELECT nome, idade FROM clientes WHERE idade > 25",
    "SELECT * FROM pedidos INNER JOIN clientes ON pedidos.cliente_id = clientes.id",
    "SELECT produto, preco FROM estoque WHERE preco <= 100 AND quantidade > 0",
    "SELECT a.nome, b.data FROM tabela_a a INNER JOIN tabela_b b ON a.id = b.id WHERE a.status = 'ativo'",

    # Exemplo com VÁRIOS JOINs
    "SELECT p.idPedido, c.Nome FROM Pedido p "
    "INNER JOIN Cliente c ON p.Cliente_idCliente = c.idCliente "
    "INNER JOIN Status s ON p.Status_idStatus = s.idStatus "
    "WHERE c.Nome = 'Joao' AND s.idStatus >= 2",

    # Consultas inválidas (devem falhar)
    "SELECT * FROM tabela WHERE coluna ~ 'regex'",  # Operador não permitido
    "SELECT * FROM tabela WHERE (coluna1 > 10 OR coluna2 < 5)",  # OR não permitido
    "DELETE FROM tabela",  # Comando não permitido
]

for i, query in enumerate(queries):
    print(f"\n--- Consulta {i+1} ---")
    print(f"SQL: {query}")
    parser = ParserSQL(query)
    parser.print_components()

import streamlit as st
import os
import tempfile
from classes import ParserSQL
from classes.grafos import gerar_grafos_otimizados

# Configuração da página
st.set_page_config(
    page_title="Processador SQL - Otimizador de Consultas",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para deixar a interface mais bonita
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stTextArea textarea {
        font-family: 'Courier New', monospace;
        font-size: 14px;
    }
    .result-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .algebra-expr {
        background-color: #f8f9fa;
        padding: 15px;
        border-left: 4px solid #4CAF50;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        margin: 10px 0;
    }
    .component-box {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    h1 {
        color: #1e3a8a;
    }
    h2 {
        color: #2563eb;
    }
    h3 {
        color: #3b82f6;
    }
    .success-msg {
        color: #22c55e;
        font-weight: bold;
    }
    .error-msg {
        color: #ef4444;
        font-weight: bold;
    }
    .example-query {
        background-color: #fef3c7;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# Título e descrição
st.title("🔍 Processador SQL - Otimizador de Consultas")
st.markdown("""
**Bem-vindo ao Processador SQL!** Este sistema analisa e otimiza consultas SQL SELECT, 
convertendo-as em álgebra relacional e gerando grafos de otimização.
""")

# Sidebar com informações
with st.sidebar:
    st.header("📚 Sobre o Projeto")
    st.markdown("""
    Este processador SQL oferece:
    
    - ✅ **Parsing de SQL** com validação de sintaxe
    - 🔄 **Conversão** para Álgebra Relacional
    - 🚀 **Otimização** com heurísticas
    - 📊 **Visualização** em grafos
    
    ### Operações Suportadas:
    - `SELECT` com colunas específicas ou `*`
    - `FROM` com aliases
    - `INNER JOIN` (múltiplos)
    - `WHERE` com operadores: `=, <, >, <=, >=, <>, AND`
    
    ### Restrições:
    - ❌ Não suporta `OR`, `NOT`, `LIKE`, `IS NULL`
    - ❌ Apenas operadores permitidos
    """)
    
    st.header("💡 Dicas")
    st.info("""
    - Use aliases em JOINs para melhor legibilidade
    - Qualifique colunas com prefixo da tabela em JOINs
    - Evite SELECT * para melhor otimização
    """)

# Queries de exemplo
st.header("📋 Exemplos de Consultas")
exemplos = {
    "Consulta Simples com WHERE": "SELECT nome, idade FROM clientes WHERE idade > 25",
    "JOIN Básico": "SELECT * FROM pedidos INNER JOIN clientes ON pedidos.cliente_id = clientes.id",
    "Múltiplas Condições": "SELECT produto, preco FROM estoque WHERE preco <= 100 AND quantidade > 0",
    "JOIN com Aliases": "SELECT a.nome, b.data FROM tabela_a a INNER JOIN tabela_b b ON a.id = b.id WHERE a.status = 'ativo'",
    "Múltiplos JOINs": """SELECT p.idPedido, c.Nome FROM Pedido p 
INNER JOIN Cliente c ON p.Cliente_idCliente = c.idCliente 
INNER JOIN Status s ON p.Status_idStatus = s.idStatus 
WHERE c.Nome = 'Joao' AND s.idStatus >= 2"""
}

cols = st.columns(3)
for idx, (nome, query) in enumerate(exemplos.items()):
    with cols[idx % 3]:
        if st.button(nome, key=f"exemplo_{idx}"):
            st.session_state.query_input = query

# Área de input da query
st.header("✏️ Digite sua Consulta SQL")
query_input = st.text_area(
    "SQL Query",
    value=st.session_state.get('query_input', ''),
    height=150,
    placeholder="Digite sua consulta SQL aqui...\nExemplo: SELECT * FROM tabela WHERE coluna = 'valor'",
    label_visibility="collapsed"
)

# Botão de análise
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    analisar = st.button("🔍 Analisar Consulta", type="primary", use_container_width=True)
with col2:
    limpar = st.button("🗑️ Limpar", use_container_width=True)

if limpar:
    st.session_state.query_input = ''
    st.rerun()

# Processamento da query
if analisar and query_input.strip():
    with st.spinner("Analisando consulta..."):
        parser = ParserSQL(query_input)
        
        if parser.eh_valido():
            st.success("✅ Consulta SQL válida!")
            
            # Componentes da query
            st.header("📦 Componentes da Consulta")
            components = parser.get_components()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="component-box">', unsafe_allow_html=True)
                st.subheader("SELECT")
                st.code(components['select'], language='sql')
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="component-box">', unsafe_allow_html=True)
                st.subheader("FROM")
                st.code(components['from'], language='sql')
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if components['joins']:
                    st.markdown('<div class="component-box">', unsafe_allow_html=True)
                    st.subheader("JOINS")
                    for i, join in enumerate(components['joins'], 1):
                        st.write(f"**JOIN {i}:** `{join['table']}`")
                        st.write(f"**ON:** `{join['on']}`")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                if components['where']:
                    st.markdown('<div class="component-box">', unsafe_allow_html=True)
                    st.subheader("WHERE")
                    st.code(components['where'], language='sql')
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Álgebra Relacional
            st.header("🔬 Álgebra Relacional")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Original")
                ra_original = parser.to_rel_algebra()
                if ra_original:
                    st.markdown(f'<div class="algebra-expr">{ra_original}</div>', unsafe_allow_html=True)
            
            with col2:
                st.subheader("Otimizada")
                ra_otimizada = parser.otimizar_algebra_relacional()
                if ra_otimizada:
                    st.markdown(f'<div class="algebra-expr">{ra_otimizada}</div>', unsafe_allow_html=True)
            
            # Gerar grafos
            st.header("📊 Grafos de Otimização")
            
            with st.spinner("Gerando grafos..."):
                # Criar diretório temporário para os grafos
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Mudar para o diretório temporário
                    old_dir = os.getcwd()
                    os.chdir(tmpdir)
                    
                    # Gerar grafos
                    gerar_grafos_otimizados(query_input, "query_temp")
                    
                    # Exibir grafos
                    grafos_dir = os.path.join(tmpdir, "grafos")
                    if os.path.exists(grafos_dir):
                        tabs = st.tabs(["🔷 Grafo Literal", "🔸 Redução de Tuplas", "🔹 Redução de Atributos"])
                        
                        grafos = [
                            ("query_temp_literal.png", "Grafo Literal - Ordem exata da query SQL"),
                            ("query_temp_tuplas.png", "Redução de Tuplas - Seleções aplicadas precocemente"),
                            ("query_temp_atributos.png", "Redução de Atributos - Projeções aplicadas precocemente")
                        ]
                        
                        for tab, (grafo_file, descricao) in zip(tabs, grafos):
                            with tab:
                                grafo_path = os.path.join(grafos_dir, grafo_file)
                                if os.path.exists(grafo_path):
                                    st.markdown(f"**{descricao}**")
                                    st.image(grafo_path, use_container_width=True)
                                else:
                                    st.warning(f"Grafo não encontrado: {grafo_file}")
                    
                    # Voltar para o diretório original
                    os.chdir(old_dir)
            
            # Explicação das otimizações
            with st.expander("ℹ️ Sobre as Heurísticas de Otimização"):
                st.markdown("""
                ### Heurísticas de Otimização de Consultas
                
                **1. Grafo Literal:**
                - Representa a ordem exata da consulta SQL original
                - Mostra FROM → JOIN(s) → WHERE → SELECT
                
                **2. Redução de Tuplas (Push-down de Seleções):**
                - Aplica filtros WHERE o mais cedo possível
                - Reduz o número de tuplas antes das junções
                - Melhora significativamente a performance
                
                **3. Redução de Atributos (Projeção Precoce):**
                - Projeta apenas colunas necessárias antes das junções
                - Reduz o tamanho dos dados intermediários
                - Otimiza uso de memória e I/O
                
                Essas otimizações seguem princípios clássicos de otimização de banco de dados
                para minimizar o custo de execução das consultas.
                """)
        
        else:
            st.error("❌ Consulta SQL inválida!")
            st.warning("""
            **Possíveis problemas:**
            - Sintaxe incorreta
            - Operadores não suportados (OR, NOT, LIKE, IS NULL, etc.)
            - Faltam palavras-chave obrigatórias (SELECT, FROM)
            - Parênteses desbalanceados
            """)

elif analisar and not query_input.strip():
    st.warning("⚠️ Por favor, digite uma consulta SQL para analisar.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280;'>
    <p>Desenvolvido com ❤️ usando Streamlit | Processador SQL v1.0</p>
</div>
""", unsafe_allow_html=True)

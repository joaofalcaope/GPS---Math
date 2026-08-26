import streamlit as st

st.set_page_config(
    page_title="GPS-Math | Sistema Diagnóstico de Matemática",
    page_icon="📐",
    layout="wide"
)

# Configuração do menu lateral oficial
st.sidebar.title("📐 GPS-Math")
st.sidebar.caption("Plataforma de Aprendizagem Adaptativa")

# Define as páginas utilizando os arquivos do projeto
pagina_aluno = st.Page("app_aluno.py", title="Painel do Aluno", icon="👤")
pagina_professor = st.Page("app_professor.py", title="Painel do Professor / Gestor", icon="📐")

# Cria a navegação no menu lateral
pg = st.navigation({
    "Acessar plataforma como:": [pagina_aluno, pagina_professor]
})

# Executa a página selecionada
pg.run()
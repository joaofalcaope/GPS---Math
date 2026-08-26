import streamlit as st

# Configuração global da página
st.set_page_config(
    page_title="GPS-Math | Sistema Diagnóstico de Matemática",
    page_icon="📐",
    layout="wide"
)

# Menu lateral de navegação/login simples
st.sidebar.title("📐 GPS-Math")
st.sidebar.caption("Plataforma de Aprendizagem Adaptativa")

perfil = st.sidebar.radio(
    "Acessar plataforma como:",
    ["👤 Painel do Aluno", "📐 Painel do Professor / Gestor"]
)

# Roteamento de telas
if perfil == "👤 Painel do Aluno":
    import app_aluno  # Executa a tela do aluno
else:
    import app_professor        # Executa a tela do professor
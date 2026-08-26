import streamlit as st

st.set_page_config(page_title="GPS-Math", page_icon="🎯", layout="wide")

# Seleção de Perfil no menu lateral ou inicial
perfil = st.sidebar.radio("Selecione o Portal de Acesso:", ["Área do Aluno", "Área do Professor"])

if perfil == "Área do Aluno":
    # Carrega a lógica da tela do aluno
    import app_aluno
else:
    # Carrega a lógica da área restrita do professor
    import app_professor
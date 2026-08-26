import os
import random
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# Configuração da página Streamlit
st.set_page_config(
    page_title="GPS-Math | Recomposição de Aprendizagem",
    page_icon="🎯",
    layout="wide"
)

# 1. Carregamento de variáveis de ambiente de forma segura (Local + Streamlit Cloud)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL and "SUPABASE_URL" in st.secrets:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]

if not SUPABASE_KEY and "SUPABASE_KEY" in st.secrets:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Credenciais do Supabase não encontradas! Verifique o arquivo .env ou a aba Settings > Secrets no Streamlit Cloud.")
    st.stop()

# Inicialização do cliente Supabase
@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()


# 2. Funções de Autenticação e Busca
def cadastrar_aluno(matricula: str, nome: str, turma: str, senha: str):
    """Insere um novo aluno na tabela 'alunos' do Supabase."""
    try:
        res = supabase.table("alunos").select("matricula").eq("matricula", matricula).execute()
        if res.data:
            return False, "Matrícula já cadastrada no sistema!"
        
        payload = {
            "matricula": matricula,
            "nome": nome,
            "turma": turma,
            "senha": senha
        }
        supabase.table("alunos").insert(payload).execute()
        return True, "Cadastro realizado com sucesso! Faça seu login."
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"


def autenticar_aluno(matricula: str, senha: str):
    """Valida a matrícula e senha na tabela 'alunos'."""
    try:
        res = supabase.table("alunos") \
            .select("matricula, nome, turma") \
            .eq("matricula", matricula) \
            .eq("senha", senha) \
            .execute()
        
        if res.data:
            return True, res.data[0]
        else:
            return False, "Matrícula ou senha incorretos."
    except Exception as e:
        return False, f"Erro ao conectar com o banco: {e}"


def carregar_respostas_aluno(matricula: str):
    """Busca as habilidades que o aluno já acertou previamente no banco."""
    try:
        res = supabase.table("respostas_alunos") \
            .select("habilidade_id") \
            .eq("matricula", matricula) \
            .eq("correto", True) \
            .execute()
        if res.data:
            return set(item["habilidade_id"] for item in res.data if item.get("habilidade_id"))
    except Exception:
        pass
    return set()


@st.cache_data(ttl=300)
def carregar_habilidades_por_unidade(unidade: str):
    """Busca habilidades e todas as questões associadas de uma Unidade Temática."""
    try:
        res_hab = supabase.table("habilidades") \
            .select("id, titulo, unidade_tematica, descricao") \
            .eq("unidade_tematica", unidade) \
            .execute()
        
        if not res_hab.data:
            return {}, {}

        habs = {h["id"]: h for h in res_hab.data}
        keys = list(habs.keys())

        res_q = supabase.table("questoes") \
            .select("*") \
            .in_("habilidade_id", keys) \
            .execute()
        
        questoes_por_hab = {}
        if res_q.data:
            for q in res_q.data:
                h_id = q["habilidade_id"]
                if h_id not in questoes_por_hab:
                    questoes_por_hab[h_id] = []
                questoes_por_hab[h_id].append(q)
            
        return habs, questoes_por_hab
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        return {}, {}


def salvar_resposta_supabase(payload: dict):
    """Salva a tentativa do aluno no Supabase."""
    try:
        supabase.table("respostas_alunos").insert(payload).execute()
    except Exception as e:
        st.error(f"Erro ao registrar progresso: {e}")


# =====================================================================
# ESTADOS DA SESSÃO (SESSION STATE)
# =====================================================================
def inicializar_estados():
    defaults = {
        "aluno_nome": "",
        "aluno_matricula": "",
        "aluno_turma": "",
        "registrado": False,
        "unidade_selecionada": None,
        "habilidade_em_treino": None,
        "modo_estudo": None,
        "consolidadas": set(),
        "questao_idx": 0,
        "resposta_enviada": False,
        "escolha_atual": None,
        "questoes_diagnostico": []
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

inicializar_estados()


# =====================================================================
# TELA 1: AUTENTICAÇÃO (LOGIN / CADASTRO) & INSTRUÇÕES
# =====================================================================
if not st.session_state.registrado:
    st.markdown("# 🎯 GPS-Math | Recomposição de Aprendizagem")
    st.markdown("##### Fortaleça sua base em matemática do Fundamental para voar no Ensino Médio!")
    
    st.divider()

    st.markdown("### 💡 Como funciona a sua recomposição?")
    col_step1, col_step2, col_step3 = st.columns(3)
    
    with col_step1:
        st.info("#### 1. Escolha o Tema\nSelecione a área da matemática em que sente necessidade de reforçar seus conceitos.")
        
    with col_step2:
        st.warning("#### 2. Faça o Diagnóstico\nRealize um teste rápido do tema para mapear quais lacunas precisam da sua atenção.")
        
    with col_step3:
        st.success("#### 3. Treino Focado\nTreine direto nas habilidades indicadas até dominar todos os tópicos prioritários.")

    st.markdown("<br>", unsafe_allow_html=True)

    tab_login, tab_cadastro = st.tabs(["🔑 Entrar (Login)", "📝 Criar Nova Conta"])

    with tab_login:
        with st.form("form_login"):
            st.subheader("Acesse sua conta")
            matricula_input = st.text_input("Matrícula:", placeholder="Digite sua matrícula")
            senha_input = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
            
            btn_entrar = st.form_submit_button("🚀 Entrar no Portal", type="primary")

            if btn_entrar:
                if not matricula_input.strip() or not senha_input.strip():
                    st.error("Por favor, preencha a Matrícula e a Senha.")
                else:
                    sucesso, aluno_dados = autenticar_aluno(matricula_input.strip(), senha_input.strip())
                    if sucesso:
                        st.session_state.aluno_nome = aluno_dados["nome"]
                        st.session_state.aluno_matricula = aluno_dados["matricula"]
                        st.session_state.aluno_turma = aluno_dados["turma"]
                        st.session_state.consolidadas = carregar_respostas_aluno(aluno_dados["matricula"])
                        st.session_state.registrado = True
                        st.rerun()
                    else:
                        st.error(aluno_dados)

    with tab_cadastro:
        with st.form("form_cadastro"):
            st.subheader("Registre seus dados")
            
            c1, c2 = st.columns(2)
            with c1:
                nova_matricula = st.text_input("Matrícula / ID:", placeholder="Ex: 20261001")
                novo_nome = st.text_input("Nome Completo:", placeholder="Ex: Maria Clara")
            with c2:
                nova_turma = st.text_input("Turma (Ensino Médio):", placeholder="Ex: 1º Ano A")
                nova_senha = st.text_input("Crie uma Senha:", type="password")

            btn_cadastrar = st.form_submit_button("✅ Concluir Cadastro", type="primary")

            if btn_cadastrar:
                if not all([nova_matricula.strip(), novo_nome.strip(), nova_turma.strip(), nova_senha.strip()]):
                    st.error("Preencha todos os campos do formulário para se cadastrar.")
                else:
                    ok, msg = cadastrar_aluno(
                        nova_matricula.strip(), 
                        novo_nome.strip(), 
                        nova_turma.strip(), 
                        nova_senha.strip()
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)


# =====================================================================
# TELA 2: SELEÇÃO DE TEMA (UNIDADE TEMÁTICA)
# =====================================================================
elif st.session_state.registrado and not st.session_state.unidade_selecionada:
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"Bem-vindo(a), {st.session_state.aluno_nome}! 👋")
        st.caption(f"Matrícula: **{st.session_state.aluno_matricula}** | Turma: **{st.session_state.aluno_turma}**")
    with col_head2:
        if st.button("🚪 Sair da Conta"):
            st.session_state.clear()
            st.rerun()

    st.divider()

    st.metric("🏆 Total de Habilidades Consolidadas até agora", len(st.session_state.consolidadas))
    st.markdown("<br>", unsafe_allow_html=True)

    unidades = [
        {"nome": "Álgebra", "icone": "📐", "desc": "Equações, expressões, funções e padrões numéricos."},
        {"nome": "Geometria", "icone": "🔺", "desc": "Áreas, perímetros, triângulos, ângulos e formas planas/espaciais."},
        {"nome": "Números", "icone": "🔢", "desc": "Operações fundamentais, frações, porcentagem e razões."},
        {"nome": "Probabilidade e Estatística", "icone": "📊", "desc": "Análise de gráficos, médias e cálculo de probabilidades."},
        {"nome": "Grandezas e Medidas", "icone": "📏", "desc": "Unidades de medida, conversões, volume e capacidade."}
    ]

    cols = st.columns(2)
    for idx, u in enumerate(unidades):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"### {u['icone']} {u['nome']}")
                st.write(u['desc'])
                if st.button(f"Estudar {u['nome']}", key=f"btn_u_{idx}", type="primary"):
                    st.session_state.unidade_selecionada = u['nome']
                    st.rerun()


# =====================================================================
# TELA 3: PAINEL DA UNIDADE (DIAGNÓSTICO VS TREINAMENTO + CONSOLIDADAS)
# =====================================================================
elif st.session_state.registrado and st.session_state.unidade_selecionada and not st.session_state.modo_estudo:
    unidade = st.session_state.unidade_selecionada
    
    def voltar_temas():
        st.session_state.unidade_selecionada = None
        st.session_state.habilidade_em_treino = None
        st.session_state.modo_estudo = None

    st.button("⬅️ Voltar para Temas", on_click=voltar_temas)
    st.title(f"Área: {unidade}")
    
    dict_habs, dict_questoes = carregar_habilidades_por_unidade(unidade)
    
    habs_tema = list(dict_habs.keys())
    habs_consolidadas_tema = [h for h in habs_tema if h in st.session_state.consolidadas]
    habs_pendentes_tema = [h for h in habs_tema if h not in st.session_state.consolidadas]

    m1, m2 = st.columns(2)
    m1.metric("📌 Habilidades a Treinar (Nesta Área)", len(habs_pendentes_tema))
    m2.metric("✅ Habilidades Consolidadas (Nesta Área)", len(habs_consolidadas_tema))

    if habs_pendentes_tema:
        prox_hab = habs_pendentes_tema[0]
        st.info(f"💡 **Sugestão de Estudo:** Comece pela habilidade `{prox_hab}` — *{dict_habs.get(prox_hab, {}).get('titulo', '')}*")

    st.divider()

    col_diag, col_treino = st.columns(2)

    with col_diag:
        with st.container(border=True):
            st.markdown("### 🩺 Passo 1: Diagnóstico do Tema")
            st.write("Responda a um teste geral com questões sortidas de diferentes habilidades desta área.")
            
            if st.button("🚀 Iniciar Diagnóstico Geral", type="primary"):
                questoes_sortidas = []
                for h_id, q_list in dict_questoes.items():
                    if q_list:
                        questoes_sortidas.append(random.choice(q_list))
                
                if questoes_sortidas:
                    random.shuffle(questoes_sortidas)
                    st.session_state.questoes_diagnostico = questoes_sortidas
                    st.session_state.modo_estudo = "DIAGNOSTICO"
                    st.session_state.questao_idx = 0
                    st.session_state.resposta_enviada = False
                    st.session_state.escolha_atual = None
                    st.rerun()
                else:
                    st.warning("Nenhuma questão cadastrada para este tema ainda.")

    with col_treino:
        with st.container(border=True):
            st.markdown("### 🎯 Passo 2: Treinamento Livre")
            st.write("Escolha diretamente qual habilidade específica deseja praticar:")
            
            if not dict_questoes:
                st.warning("Nenhuma questão cadastrada para este tema ainda.")
            else:
                hab_escolhida = st.selectbox(
                    "Selecione uma Habilidade:",
                    options=habs_tema,
                    format_func=lambda x: f"{'✅' if x in st.session_state.consolidadas else '📌'} {x} - {dict_habs.get(x, {}).get('titulo', '')}"
                )
                
                if st.button("⚡ Treinar Habilidade Selecionada"):
                    st.session_state.habilidade_em_treino = hab_escolhida
                    st.session_state.modo_estudo = "TREINAMENTO"
                    st.session_state.questao_idx = 0
                    st.session_state.resposta_enviada = False
                    st.session_state.escolha_atual = None
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📊 Ver Status Detalhado das Habilidades do Tema"):
        for h_id in habs_tema:
            status = "✅ Consolidada" if h_id in st.session_state.consolidadas else "⏳ Em Aberto"
            st.markdown(f"**{h_id}**: {dict_habs[h_id]['titulo']} — `{status}`")


# =====================================================================
# TELA 4: EXECUÇÃO DOS EXERCÍCIOS (DIAGNÓSTICO OU TREINAMENTO)
# =====================================================================
elif st.session_state.modo_estudo:
    modo = st.session_state.modo_estudo
    dict_habs, dict_questoes = carregar_habilidades_por_unidade(st.session_state.unidade_selecionada)

    if modo == "DIAGNOSTICO":
        questoes = st.session_state.questoes_diagnostico
    else:
        h_id = st.session_state.habilidade_em_treino
        questoes = dict_questoes.get(h_id, [])

    def avancar_questao():
        st.session_state.questao_idx += 1
        st.session_state.resposta_enviada = False
        st.session_state.escolha_atual = None

    def sair_exercicio():
        st.session_state.modo_estudo = None
        st.session_state.habilidade_em_treino = None
        st.session_state.questao_idx = 0
        st.session_state.resposta_enviada = False
        st.session_state.escolha_atual = None
        st.session_state.questoes_diagnostico = []

    st.button("⬅️ Sair do Exercício", on_click=sair_exercicio)

    idx = st.session_state.questao_idx
    total_q = len(questoes)

    if total_q > 0 and idx < total_q:
        q = questoes[idx]
        hab_atual = q["habilidade_id"]
        
        st.subheader(f"[{modo}] Questão {idx + 1} de {total_q} — Habilidade: {hab_atual}")
        st.caption(f"Descrição: {dict_habs.get(hab_atual, {}).get('titulo', '')}")
        st.progress((idx + 1) / total_q)
        st.divider()

        st.markdown(f"### {q['enunciado']}")
        
        opcoes = {
            f"A) {q['opcao_a']}": "A",
            f"B) {q['opcao_b']}": "B",
            f"C) {q['opcao_c']}": "C",
            f"D) {q['opcao_d']}": "D"
        }
        
        escolha = st.radio(
            "Escolha a alternativa correta:", 
            list(opcoes.keys()), 
            index=None, 
            key=f"q_radio_{q['id']}_{idx}",
            disabled=st.session_state.resposta_enviada
        )

        if not st.session_state.resposta_enviada:
            if st.button("Enviar Resposta", type="primary"):
                if not escolha:
                    st.warning("Selecione uma opção antes de enviar.")
                else:
                    letra_marcada = opcoes[escolha]
                    correta = str(q["resposta_correta"]).upper().strip()
                    is_correto = (letra_marcada == correta)

                    salvar_resposta_supabase({
                        "matricula": st.session_state.aluno_matricula,
                        "aluno_nome": st.session_state.aluno_nome,
                        "questao_id": q["id"],
                        "habilidade_id": hab_atual,
                        "opcao_marcada": letra_marcada,
                        "correto": is_correto
                    })

                    if is_correto:
                        st.session_state.consolidadas.add(hab_atual)

                    st.session_state.escolha_atual = escolha
                    st.session_state.resposta_enviada = True
                    st.rerun()

        if st.session_state.resposta_enviada:
            escolha_feita = st.session_state.escolha_atual
            if escolha_feita in opcoes:
                letra_marcada = opcoes[escolha_feita]
                correta = str(q["resposta_correta"]).upper().strip()
                is_correto = (letra_marcada == correta)

                if is_correto:
                    st.success("🎉 **Excelente! Você acertou!**")
                    st.info(f"💡 **Explicação:** {q.get('explicacao_correta', 'Sem explicação cadastrada.')}")
                else:
                    st.error("❌ **Resposta incorreta.**")
                    letra_erro = letra_marcada.lower()
                    diag = q.get(f"diagnostico_erro_{letra_erro}")
                    reg = q.get(f"habilidade_regressao_{letra_erro}")
                    
                    st.warning(f"🧠 **Diagnóstico do erro:** {diag or 'Revise os passos de cálculo desta questão.'}")
                    if reg:
                        st.info(f"📌 **Recomendação de Recomposição:** Recomendamos revisar a habilidade `{reg}`.")

            st.markdown("---")
            
            if idx + 1 < total_q:
                st.button("▶️ Próxima Questão", type="primary", on_click=avancar_questao)
            else:
                st.balloons()
                st.success(f"🏆 **Você concluiu o {modo} deste tema!**")
                st.button("Voltar para o Painel da Área", on_click=sair_exercicio)
    else:
        st.info("Nenhuma questão encontrada.")
        st.button("Voltar ao Painel", on_click=sair_exercicio)
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client, Client

# Configuração da página Streamlit
st.set_page_config(
    page_title="GPS-Math | Painel Diagnóstico do Professor",
    page_icon="📐",
    layout="wide"
)

# 1. Conexão com o Supabase (Suporta ambiente Local e Streamlit Cloud)
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Chaves do Supabase não encontradas no arquivo .env ou Secrets!")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()


# 2. Carregamento e Tratamento de Dados com Cache
@st.cache_data(ttl=60)
def carregar_dados_completos():
    try:
        res_alunos = supabase.table("alunos").select("matricula, nome, turma").execute()
        res_respostas = supabase.table("respostas_alunos").select("*").execute()
        res_habilidades = supabase.table("habilidades").select("id, titulo, unidade_tematica, ano").execute()
        res_questoes = supabase.table("questoes").select("*").execute()

        df_alunos = pd.DataFrame(res_alunos.data or [])
        df_respostas = pd.DataFrame(res_respostas.data or [])
        df_habilidades = pd.DataFrame(res_habilidades.data or [])
        df_questoes = pd.DataFrame(res_questoes.data or [])

        return df_alunos, df_respostas, df_habilidades, df_questoes
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


df_alunos, df_respostas, df_habilidades, df_questoes = carregar_dados_completos()

st.title("📐 GPS-Math — Painel de Gestão e Diagnóstico Pedagógico")
st.caption("Acompanhamento de turmas, análise de distratores, recomposição e moderação do banco de questões.")

# Tratar colunas caso existam respostas
if not df_respostas.empty:
    df_respostas['correto'] = df_respostas['correto'].astype(bool)
    if 'created_at' in df_respostas.columns:
        df_respostas['data_resposta'] = pd.to_datetime(df_respostas['created_at'])
    else:
        df_respostas['data_resposta'] = pd.Timestamp.now()
    if 'tempo_segundos' not in df_respostas.columns:
        df_respostas['tempo_segundos'] = 45 

    df_full = df_respostas.merge(df_alunos, on="matricula", how="inner")
else:
    df_full = pd.DataFrame()

dict_hab_titulo = {}
if not df_habilidades.empty:
    dict_hab_titulo = dict(zip(df_habilidades['id'], df_habilidades['titulo']))


# =====================================================================
# BARRA LATERAL (FILTROS E EXPORTAÇÃO)
# =====================================================================
st.sidebar.header("🔍 Filtros de Visualização")

lista_turmas = ["Todas as Turmas"] + sorted(list(df_alunos['turma'].unique())) if not df_alunos.empty else ["Todas as Turmas"]
turma_selecionada = st.sidebar.selectbox("Selecione a Turma:", lista_turmas)

# Filtrar subconjunto
if not df_full.empty and turma_selecionada != "Todas as Turmas":
    df_filtrado = df_full[df_full['turma'] == turma_selecionada]
    alunos_turma = df_alunos[df_alunos['turma'] == turma_selecionada]
else:
    df_filtrado = df_full.copy()
    alunos_turma = df_alunos.copy()

lista_alunos = ["Todos os Alunos"] + sorted(list(alunos_turma['nome'].unique())) if not alunos_turma.empty else ["Todos os Alunos"]
aluno_selecionado = st.sidebar.selectbox("Selecione o Aluno (Opcional):", lista_alunos)

if not df_filtrado.empty and aluno_selecionado != "Todos os Alunos":
    df_filtrado = df_filtrado[df_filtrado['nome'] == aluno_selecionado]

# Exportador CSV na Sidebar
st.sidebar.divider()
st.sidebar.subheader("📥 Exportar Relatórios")
if not df_filtrado.empty:
    csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📄 Baixar Relatório em CSV",
        data=csv_data,
        file_name=f"relatorio_gps_math_{turma_selecionada}.csv",
        mime="text/csv"
    )


# =====================================================================
# INTERFACE PRINCIPAL - ABAS DIAGNÓSTICAS E EDITORA DE QUESTÕES
# =====================================================================
tab_turma, tab_alunos, tab_moderação, tab_banco = st.tabs([
    "📊 Diagnóstico da Turma", 
    "👤 Análise do Aluno", 
    "🛠️ Edição & Moderação",
    "📚 Cobertura BNCC"
])

# ---------------------------------------------------------------------
# ABA 1: DIAGNÓSTICO DA TURMA
# ---------------------------------------------------------------------
with tab_turma:
    st.header(f"📈 Visão Diagnóstica: {turma_selecionada}")

    if df_filtrado.empty:
        st.info("Ainda não há registros de respostas salvos para a turma/filtro selecionado.")
    else:
        tot_questoes = len(df_filtrado)
        tot_acertos = df_filtrado['correto'].sum()
        taxa_geral = (tot_acertos / tot_questoes) * 100 if tot_questoes > 0 else 0
        tempo_medio = df_filtrado['tempo_segundos'].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Alunos Ativos", len(alunos_turma))
        m2.metric("Questões Respondidas", tot_questoes)
        m3.metric("Taxa Média de Acerto", f"{taxa_geral:.1f}%")
        m4.metric("Tempo Médio/Questão", f"{tempo_medio:.0f}s")

        st.divider()

        # MATRIZ DE CALOR (HEATMAP)
        st.subheader("🔥 Matriz de Desempenho (Alunos × Habilidades)")
        pivot_turma = df_filtrado.pivot_table(
            index="nome",
            columns="habilidade_id",
            values="correto",
            aggfunc="mean"
        ).fillna(0) * 100

        if not pivot_turma.empty:
            fig_heatmap = px.imshow(
                pivot_turma,
                labels=dict(x="Habilidade", y="Aluno", color="% Acerto"),
                color_continuous_scale="RdYlGn",
                text_auto=".0f",
                aspect="auto"
            )
            fig_heatmap.update_layout(height=max(350, len(pivot_turma) * 25))
            st.plotly_chart(fig_heatmap, use_container_width=True)

        st.divider()

        # HABILIDADES CRÍTICAS
        hab_stats = df_filtrado.groupby("habilidade_id").agg(
            total=("correto", "count"),
            acertos=("correto", "sum")
        ).reset_index()
        hab_stats["taxa_acerto"] = (hab_stats["acertos"] / hab_stats["total"]) * 100

        st.subheader("🚨 Habilidades com Menor Desempenho")
        piores = hab_stats.sort_values(by="taxa_acerto").head(5)
        
        if not piores.empty:
            fig_bar_erros = px.bar(
                piores, x="taxa_acerto", y="habilidade_id", orientation="h",
                color="taxa_acerto", color_continuous_scale="Reds_r",
                text_auto=".1f%", title="Habilidades com Maior % de Erros"
            )
            fig_bar_erros.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_bar_erros, use_container_width=True)


# ---------------------------------------------------------------------
# ABA 2: ANÁLISE INDIVIDUAL DO ALUNO
# ---------------------------------------------------------------------
with tab_alunos:
    st.header("👤 Diagnóstico Individual do Aluno")

    if aluno_selecionado == "Todos os Alunos":
        st.info("👈 Selecione um aluno no menu lateral para visualizar o relatório detalhado.")
    elif df_filtrado.empty:
        st.warning("Este aluno ainda não possui respostas cadastradas.")
    else:
        tot_al = len(df_filtrado)
        ac_al = df_filtrado['correto'].sum()
        tx_al = (ac_al / tot_al) * 100
        tempo_al = df_filtrado['tempo_segundos'].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Aproveitamento Geral", f"{tx_al:.1f}%")
        c2.metric("Questões Respondidas", tot_al)
        c3.metric("Tempo Médio p/ Questão", f"{tempo_al:.0f}s")

        st.divider()
        st.subheader("🕸️ Desempenho do Aluno por Habilidade")
        al_hab = df_filtrado.groupby("habilidade_id").agg(taxa=("correto", lambda x: x.mean() * 100)).reset_index()

        fig_radar = px.line_polar(
            al_hab, r='taxa', theta='habilidade_id', line_close=True,
            title=f"Mapeamento de Habilidades - {aluno_selecionado}"
        )
        fig_radar.update_traces(fill='toself')
        st.plotly_chart(fig_radar, use_container_width=True)


# ---------------------------------------------------------------------
# ABA 3: MODERAÇÃO E CORREÇÃO DE GABARITO (NOVO MÓDULO)
# ---------------------------------------------------------------------
with tab_moderação:
    st.header("🛠️ Moderação e Edição de Questões / Gabarito")
    st.caption("Localize questões cadastradas via IA ou manual, corrija gabaritos incorretos e atualize as opções do banco de dados.")

    if df_questoes.empty:
        st.warning("Nenhuma questão foi encontrada na tabela 'questoes' do Supabase.")
    else:
        # Métodos de Busca
        col_busca1, col_busca2 = st.columns([1, 2])
        
        with col_busca1:
            metodo_busca = st.radio("Buscar questão por:", ["ID da Questão", "Filtrar por Habilidade"])

        questao_alvo = None

        if metodo_busca == "ID da Questão":
            with col_busca2:
                id_input = st.number_input("Digite o ID exato da questão:", min_value=1, step=1, value=1)
                q_filtradas = df_questoes[df_questoes["id"] == id_input]
                if not q_filtradas.empty:
                    questao_alvo = q_filtradas.iloc[0].to_dict()
                else:
                    st.error(f"Nenhuma questão encontrada com o ID {id_input}.")

        else:
            with col_busca2:
                lista_habs_q = sorted(list(df_questoes["habilidade_id"].dropna().unique()))
                hab_sel = st.selectbox("Selecione a Habilidade:", lista_habs_q)
                
                q_hab = df_questoes[df_questoes["habilidade_id"] == hab_sel]
                
                # Criar dropdown formatado para as questões da habilidade
                opcoes_q = {
                    row["id"]: f"ID {row['id']} - {row['enunciado'][:60]}..." 
                    for _, row in q_hab.iterrows()
                }
                if opcoes_q:
                    q_id_sel = st.selectbox("Selecione a Questão:", options=list(opcoes_q.keys()), format_func=lambda x: opcoes_q[x])
                    questao_alvo = df_questoes[df_questoes["id"] == q_id_sel].iloc[0].to_dict()

        st.divider()

        # FORMULÁRIO DE EDIÇÃO E EDICAO DE GABARITO
        if questao_alvo:
            st.subheader(f"📝 Editando Questão #ID: {questao_alvo['id']} (Habilidade: {questao_alvo.get('habilidade_id')})")
            
            with st.form("form_edicao_questao"):
                # Enunciado
                novo_enunciado = st.text_area("Enunciado da Questão:", value=questao_alvo.get("enunciado", ""), height=100)
                
                # Alternativas
                col_a, col_b = st.columns(2)
                with col_a:
                    opt_a = st.text_input("Opção (A):", value=questao_alvo.get("opcao_a", ""))
                    opt_b = st.text_input("Opção (B):", value=questao_alvo.get("opcao_b", ""))
                with col_b:
                    opt_c = st.text_input("Opção (C):", value=questao_alvo.get("opcao_d", ""))
                    opt_d = st.text_input("Opção (D):", value=questao_alvo.get("opcao_d", ""))

                st.divider()

                # GABARITO CORRETO E EXPLICAÇÃO
                c_gab, c_dif = st.columns([1, 1])
                with c_gab:
                    gabarito_atual = str(questao_alvo.get("resposta_correta", "A")).upper().strip()
                    opcoes_letras = ["A", "B", "C", "D"]
                    idx_default = opcoes_letras.index(gabarito_atual) if gabarito_atual in opcoes_letras else 0
                    
                    novo_gabarito = st.selectbox(
                        "🎯 RESPOSTA CORRETA (GABARITO):", 
                        options=opcoes_letras, 
                        index=idx_default,
                        help="Selecione a letra correta para esta questão."
                    )
                
                with c_dif:
                    dificuldade_atual = questao_alvo.get("dificuldade", "Media")
                    nova_dificuldade = st.selectbox("Nível de Dificuldade:", ["Facil", "Media", "Dificil"], index=0 if dificuldade_atual == "Facil" else 1)

                nova_explicacao = st.text_area("Explicação da Resposta Correta:", value=questao_alvo.get("explicacao_correta", ""), height=80)

                st.write("")
                recalcular_alunos = st.checkbox(
                    "🔄 **Recalcular notas dos alunos que já responderam a esta questão**", 
                    value=True,
                    help="Se marcado, atualiza automaticamente se o aluno acertou/errou esta questão no histórico das turmas."
                )

                btn_salvar = st.form_submit_button("💾 Salvar Alterações no Supabase", type="primary")

                if btn_salvar:
                    try:
                        # 1. Atualizar a questão na tabela
                        dados_atualizados = {
                            "enunciado": novo_enunciado,
                            "opcao_a": opt_a,
                            "opcao_b": opt_b,
                            "opcao_c": opt_c,
                            "opcao_d": opt_d,
                            "resposta_correta": novo_gabarito,
                            "dificuldade": nova_dificuldade,
                            "explicacao_correta": nova_explicacao
                        }
                        
                        supabase.table("questoes").update(dados_atualizados).eq("id", questao_alvo["id"]).execute()
                        
                        # 2. Se marcado, recalcula o histórico de respostas dos alunos
                        if recalcular_alunos and not df_respostas.empty:
                            # Busca todas as respostas cadastradas para essa questão
                            res_resp = supabase.table("respostas_alunos").select("id, opcao_marcada").eq("questao_id", questao_alvo["id"]).execute()
                            respostas_q = res_resp.data or []
                            
                            for r in respostas_q:
                                novo_status = (str(r.get("opcao_marcada")).upper().strip() == novo_gabarito)
                                supabase.table("respostas_alunos").update({"correto": novo_status}).eq("id", r["id"]).execute()

                        st.success(f"✅ Questão #{questao_alvo['id']} atualizada com sucesso no banco de dados!")
                        st.cache_data.clear() # Limpa o cache do Streamlit para atualizar os gráficos
                        
                    except Exception as err:
                        st.error(f"Erro ao salvar alterações no Supabase: {err}")


# ---------------------------------------------------------------------
# ABA 4: COBERTURA DO BANCO DE DADOS & BNCC
# ---------------------------------------------------------------------
with tab_banco:
    st.header("📚 Cobertura das Habilidades da BNCC")

    if not df_habilidades.empty:
        tot_h = len(df_habilidades)
        hab_com_q = set(df_questoes["habilidade_id"].unique()) if not df_questoes.empty else set()
        
        df_habilidades["possui_questao"] = df_habilidades["id"].apply(lambda x: x in hab_com_q)
        tot_q = df_habilidades["possui_questao"].sum()
        pct = (tot_q / tot_h) * 100 if tot_h > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Total de Habilidades (EF II)", tot_h)
        k2.metric("Habilidades com Questões Cadastradas", tot_q)
        k3.metric("Cobertura do Banco", f"{pct:.1f}%")

        st.progress(pct / 100)
        st.divider()

        st.dataframe(
            df_habilidades[["id", "ano", "unidade_tematica", "titulo", "possui_questao"]],
            use_container_width=True
        )
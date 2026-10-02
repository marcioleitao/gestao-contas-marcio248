import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import re
from datetime import datetime

# Configuração da página para navegação responsiva (Tablet / Mobile / Desktop)
st.set_page_config(
    page_title="Gestão Financeira & Cartão",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada (Tema Escuro / Moderno)
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 700;
        color: #00E676;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E2640;
        border-radius: 8px 8px 0px 0px;
        padding-left: 16px;
        padding-right: 16px;
        color: #A0AEC0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2D3748 !important;
        color: #6366F1 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNÇÕES DE PROCESSAMENTO DO PDF
# ---------------------------------------------------------
def categorizar_estabelecimento(nome, eh_parcelado):
    if eh_parcelado:
        return "Parcelamentos Fixos"
    
    nome_upper = nome.upper()
    if any(k in nome_upper for k in ["DROGARIA", "RAIA", "FARMACIA", "MED"]):
        return "Farmácia & Saúde"
    elif any(k in nome_upper for k in ["SUPERMERCADO", "PADARIA", "OAKBERRY", "ALIMENTOS", "BEER", "MERCADO"]):
        return "Alimentação & Mercado"
    elif any(k in nome_upper for k in ["VIP ITAIPU", "POSTO", "COMBUSTIVEL", "SHELL", "BR"]):
        return "Combustível & Posto"
    elif any(k in nome_upper for k in ["TOTALPASS", "ACADEMIA", "GYM"]):
        return "Fitness & Bem-Estar"
    elif any(k in nome_upper for k in ["TIM", "CLARO", "VIVO", "SOCIO", "FLUMINENSE"]):
        return "Assinaturas & Telefonia"
    else:
        return "Outros & Gerais"

def extrair_transacoes_pdf(file_bytes):
    transacoes = []
    
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                match = re.search(r'(\d{2}/\d{2})\s+\|\s+(.*?)\s+\|\s+BRL\s+([\d\.,]+)', line)
                if match:
                    data_str, desc, valor_str = match.groups()
                    if desc.strip() in ["SALDO ANTERIOR", "TOTAL DA FATURA", "TOTAL PARA MARCIO LEITAO"]:
                        continue
                    
                    try:
                        valor_clean = valor_str.replace('.', '').replace(',', '.')
                        valor = float(valor_clean)
                        eh_parcela = bool(re.search(r'\d+/\d+', desc))
                        categoria = categorizar_estabelecimento(desc, eh_parcela)
                        
                        transacoes.append({
                            "Data": data_str,
                            "Descrição": desc.strip(),
                            "Valor": valor,
                            "Parcelado": eh_parcela,
                            "Categoria": categoria
                        })
                    except ValueError:
                        continue
                        
    return pd.DataFrame(transacoes)

# ---------------------------------------------------------
# SIDEBAR - CONFIGURAÇÕES & ENTRADAS DE DADOS
# ---------------------------------------------------------
st.sidebar.title("⚙️ Painel de Controle")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("1. Carregar PDF do Cartão", type=["pdf"])

st.sidebar.subheader("🎯 Configurações de Meta")
meta_fatura = st.sidebar.number_input("Meta de Gastos no Cartão (R$)", value=5000.0, step=100.0)
dia_fechamento = st.sidebar.number_input("Dia de Fechamento do Cartão", value=23, min_value=1, max_value=31)

st.sidebar.subheader("📌 Gastos Agendados do Cartão")
corte_cabelo = st.sidebar.number_input("Gastos Avulsos (Ex: Corte R$125)", value=125.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🏠 Contas Fora do Cartão (Pix / Boleto)")

val_aluguel = st.sidebar.number_input("Aluguel / Condomínio (R$)", value=0.0, step=100.0)
val_luz = st.sidebar.number_input("Conta de Luz (R$)", value=0.0, step=10.0)
val_gas = st.sidebar.number_input("Gás / Água (R$)", value=0.0, step=10.0)
val_outros = st.sidebar.number_input("Outros Boletos / Serviços (R$)", value=0.0, step=50.0)

total_despesas_externas = val_aluguel + val_luz + val_gas + val_outros

data_hoje = datetime(2026, 10, 1)
data_fechamento = datetime(2026, 10, dia_fechamento)
dias_restantes = (data_fechamento - data_hoje).days

# ---------------------------------------------------------
# PAINEL PRINCIPAL
# ---------------------------------------------------------
st.title("🚀 Copiloto Financeiro Integrado")
st.caption(f"Data Base: **{data_hoje.strftime('%d/%m/%Y')}** | Fechamento Cartão: **{data_fechamento.strftime('%d/%m/%Y')}** ({dias_restantes} dias restantes)")

if uploaded_file is not None:
    df_fatura = extrair_transacoes_pdf(uploaded_file)
    
    if not df_fatura.empty:
        total_cartao = df_fatura["Valor"].sum()
        saldo_cartao_restante = meta_fatura - total_cartao - corte_cabelo
        meta_diaria = saldo_cartao_restante / dias_restantes if dias_restantes > 0 else 0
        total_geral_mes = total_cartao + total_despesas_externas

        # --- CARDS DE MÉTRICAS (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Acumulado no Cartão", f"R$ {total_cartao:,.2f}")
        col2.metric("Saldo Cartão P/ Gastar", f"R$ {saldo_cartao_restante:,.2f}", delta=f"Teto R$ {meta_fatura:,.0f}")
        col3.metric("Meta Diária Cartão", f"R$ {meta_diaria:,.2f}/dia", help=f"Restam {dias_restantes} dias e R${corte_cabelo:.2f} previstos")
        col4.metric("Contas Externas (Boletos/Pix)", f"R$ {total_despesas_externas:,.2f}")

        # --- BARRA DE PROGRESSO DA META DO CARTÃO ---
        progresso_pct = min(1.0, total_cartao / meta_fatura)
        st.markdown(f"**Progresso da Meta do Cartão de R$ {meta_fatura:,.2f}:** ({progresso_pct*100:.1f}% utilizado)")
        st.progress(progresso_pct)

        st.markdown("---")

        # --- ABAS COM GRÁFICOS E COMPOSIÇÃO TOTAL ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Acumulado Cartão", 
            "🏪 Estabelecimentos", 
            "📊 Categorias Cartão", 
            "🏠 Orçamento Total (Geral)",
            "📋 Extrato Cartão"
        ])

        with tab1:
            st.subheader("Evolução dos Gastos vs. Limite da Meta")
            df_timeline = df_fatura.groupby("Data")["Valor"].sum().reset_index()
            df_timeline["Soma Acumulada"] = df_timeline["Valor"].cumsum()
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_timeline["Data"], 
                y=df_timeline["Soma Acumulada"], 
                mode='lines+markers',
                name='Acumulado Realizado (R$)',
                line=dict(color='#00E676', width=3),
                fill='tozeroy'
            ))
            
            fig_line.add_hline(y=meta_fatura, line_dash="dash", line_color="#FF5252", annotation_text="Teto Meta Cartão (R$ 5.000)")

            fig_line.update_layout(
                template="plotly_dark",
                height=400,
                xaxis_title="Data do Lançamento",
                yaxis_title="Valor Acumulado (R$)",
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_line, use_container_width=True)

        with tab2:
            st.subheader("Ranking por Estabelecimento (Cartão)")
            df_estab = df_fatura.groupby("Descrição")["Valor"].sum().sort_values(ascending=True).reset_index()
            
            fig_bar = px.bar(
                df_estab, 
                x="Valor", 
                y="Descrição", 
                orientation='h',
                text_auto='.2f',
                color="Valor",
                color_continuous_scale="Purples"
            )
            fig_bar.update_layout(
                template="plotly_dark",
                height=450,
                xaxis_title="Total Gasto (R$)",
                yaxis_title="Estabelecimento",
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab3:
            st.subheader("Categorias de Compra no Cartão")
            df_cat = df_fatura.groupby("Categoria")["Valor"].sum().reset_index()
            
            fig_pie = px.pie(
                df_cat, 
                values="Valor", 
                names="Categoria", 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                template="plotly_dark",
                height=400,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab4:
            st.subheader("Composição do Seu Custo de Vida no Mês (Geral)")
            
            dados_gerais = [
                {"Origem": "Cartão de Crédito", "Tipo": "Variável / Fatura", "Valor": total_cartao},
                {"Origem": "Aluguel / Condomínio", "Tipo": "Fixa (Fora do Cartão)", "Valor": val_aluguel},
                {"Origem": "Conta de Luz", "Tipo": "Fixa (Fora do Cartão)", "Valor": val_luz},
                {"Origem": "Gás / Água", "Tipo": "Fixa (Fora do Cartão)", "Valor": val_gas},
                {"Origem": "Outros Boletos", "Tipo": "Fixa (Fora do Cartão)", "Valor": val_outros},
            ]
            df_geral = pd.DataFrame(dados_gerais)
            df_geral = df_geral[df_geral["Valor"] > 0]

            fig_geral = px.bar(
                df_geral, 
                x="Origem", 
                y="Valor", 
                color="Tipo", 
                text_auto='.2f',
                title=f"Total Compromissado no Mês: R$ {total_geral_mes:,.2f}"
            )
            fig_geral.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig_geral, use_container_width=True)

        with tab5:
            st.subheader("Todas as Transações do Cartão")
            st.dataframe(df_fatura, use_container_width=True)

    else:
        st.error("Não foi possível identificar transações no PDF carregado.")
else:
    st.info("👈 Faça o upload do PDF do cartão e preencha as contas fixas na barra lateral para ver a análise completa!")

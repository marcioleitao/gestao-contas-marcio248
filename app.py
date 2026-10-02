import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import re
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="FinPulse | Copiloto Financeiro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# STYLING CSS CUSTOMIZADO (Design Moderno & Glassmorphism)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Fundo Principal e Tipografia */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background: #0B0E14;
        color: #F3F4F6;
    }

    /* Ocultar elementos nativos desnecessários */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Top Banner / Header Customizado */
    .header-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px 32px;
        margin-bottom: 28px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }
    
    .header-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .header-subtitle {
        color: #9CA3AF;
        font-size: 0.95rem;
        margin-top: 6px;
        font-weight: 400;
    }

    /* Cards de Métricas (KPIs) com Design Neumórfico / Glass */
    .kpi-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }

    .kpi-label {
        font-size: 0.825rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }

    .kpi-sub {
        font-size: 0.8rem;
        color: #10B981;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Tabs Personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: rgba(17, 24, 39, 0.5);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 10px;
        padding: 0px 20px;
        color: #9CA3AF;
        font-weight: 600;
        font-size: 0.9rem;
        border: none;
        background-color: transparent;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
    }

    /* Sidebar Estilizada */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNÇÃO DE LEITURA DO PDF
# ---------------------------------------------------------
def categorizar_estabelecimento(nome, eh_parcelado):
    if eh_parcelado:
        return "Parcelamentos Fixos"
    
    nome_upper = nome.upper()
    if any(k in nome_upper for k in ["DROGARIA", "RAIA", "FARMACIA", "MED", "DROGASIL", "PAGLESS"]):
        return "Farmácia & Saúde"
    elif any(k in nome_upper for k in ["SUPERMERCADO", "PADARIA", "OAKBERRY", "ALIMENTOS", "BEER", "MERCADO", "RESTAURANTE", "IFOOD", "UBER EATS"]):
        return "Alimentação & Mercado"
    elif any(k in nome_upper for k in ["VIP ITAIPU", "POSTO", "COMBUSTIVEL", "SHELL", "BR", "IPIRANGA", "AUTO POSTO"]):
        return "Combustível & Posto"
    elif any(k in nome_upper for k in ["TOTALPASS", "ACADEMIA", "GYM", "SMARTFIT"]):
        return "Fitness & Bem-Estar"
    elif any(k in nome_upper for k in ["TIM", "CLARO", "VIVO", "SOCIO", "FLUMINENSE", "NETFLIX", "SPOTIFY", "PRIME"]):
        return "Assinaturas & Telefonia"
    elif any(k in nome_upper for k in ["UBER", "99", "ESTACIONAMENTO"]):
        return "Transporte & Mobilidade"
    else:
        return "Outros & Gerais"

def extrair_transacoes_pdf(file_bytes):
    transacoes = []
    ignorar_palavras = [
        "SALDO ANTERIOR", "TOTAL DA FATURA", "TOTAL PARA", "PAGAMENTO DE FATURA",
        "PAGAMENTO EFETUADO", "SUBTOTAL", "LIMITE", "SALDO ATUAL", "RESUMO DA FATURA",
        "PAGAMENTO RECEBIDO", "CRÉDITO", "ENCARGOS"
    ]
    
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                line_upper = line.upper().strip()
                if any(p in line_upper for p in ignorar_palavras):
                    continue
                
                match_data = re.match(r'^(\d{2}/\d{2}(?:/\d{2,4})?)[\s\|]+(.+)', line.strip())
                if match_data:
                    data_str = match_data.group(1)
                    resto = match_data.group(2)
                    
                    match_valor = re.search(r'(?:BRL|R\$)?\s*(-?[\d\.]+\,\d{2})\s*$', resto)
                    if match_valor:
                        valor_str = match_valor.group(1)
                        desc = resto[:match_valor.start()].strip(" |-")
                        
                        if not desc:
                            continue
                            
                        try:
                            valor_clean = valor_str.replace('.', '').replace(',', '.')
                            valor = float(valor_clean)
                            if valor <= 0:
                                continue
                                
                            eh_parcela = bool(re.search(r'\d+/\d+', desc))
                            categoria = categorizar_estabelecimento(desc, eh_parcela)
                            
                            transacoes.append({
                                "Data": data_str,
                                "Descrição": desc,
                                "Valor": valor,
                                "Parcelado": eh_parcela,
                                "Categoria": categoria
                            })
                        except ValueError:
                            continue

    df = pd.DataFrame(transacoes)
    if not df.empty:
        df = df.drop_duplicates()
    return df

# ---------------------------------------------------------
# SIDEBAR CONTROL PANEL
# ---------------------------------------------------------
st.sidebar.markdown("### ⚡ FinPulse Control")
st.sidebar.markdown("<p style='color: #6B7280; font-size: 0.85rem;'>Ajuste as suas metas e importação de faturas.</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("📂 Importar Fatura PDF", type=["pdf"])

st.sidebar.markdown("#### 🎯 Metas & Planeamento")
meta_fatura = st.sidebar.number_input("Meta de Gastos no Cartão (R$)", value=5000.0, step=100.0)
dia_fechamento = st.sidebar.number_input("Dia de Fechamento", value=23, min_value=1, max_value=31)
corte_cabelo = st.sidebar.number_input("Reserva / Avulsos (R$)", value=125.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🏠 Despesas Fora do Cartão")

val_aluguel = st.sidebar.number_input("Aluguel / Condomínio (R$)", value=0.0, step=100.0)
val_luz = st.sidebar.number_input("Luz / Energia (R$)", value=0.0, step=10.0)
val_gas = st.sidebar.number_input("Gás / Água (R$)", value=0.0, step=10.0)
val_outros = st.sidebar.number_input("Outros Boletos / Pix (R$)", value=0.0, step=50.0)

total_despesas_externas = val_aluguel + val_luz + val_gas + val_outros

hoje = datetime.now()
try:
    data_fechamento = datetime(hoje.year, hoje.month, int(dia_fechamento))
    if hoje > data_fechamento:
        prox_mes = hoje.month + 1 if hoje.month < 12 else 1
        prox_ano = hoje.year if hoje.month < 12 else hoje.year + 1
        data_fechamento = datetime(prox_ano, prox_mes, int(dia_fechamento))
except ValueError:
    data_fechamento = hoje

dias_restantes = max(0, (data_fechamento - hoje).days)

# ---------------------------------------------------------
# PAINEL PRINCIPAL
# ---------------------------------------------------------
# Top Banner
st.markdown(f"""
<div class="header-container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
            <h1 class="header-title">Copiloto Financeiro Integrado</h1>
            <div class="header-subtitle">Visão inteligente de gastos, metas e orçamentos em tempo real.</div>
        </div>
        <div style="text-align: right;">
            <span style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #818CF8; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                📅 Fechamento: {data_fechamento.strftime('%d/%m/%Y')} ({dias_restantes} dias)
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if uploaded_file is not None:
    df_fatura = extrair_transacoes_pdf(uploaded_file)
    
    if not df_fatura.empty:
        total_cartao = df_fatura["Valor"].sum()
        saldo_cartao_restante = meta_fatura - total_cartao - corte_cabelo
        meta_diaria = saldo_cartao_restante / dias_restantes if dias_restantes > 0 else 0
        total_geral_mes = total_cartao + total_despesas_externas

        # --- CARDS DE MÉTRICAS DESIGN NATIVO/CUSTOM ---
        kcol1, kcol2, kcol3, kcol4 = st.columns(4)
        
        with kcol1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Cartão Acumulado</div>
                <div class="kpi-value">R$ {total_cartao:,.2f}</div>
                <div class="kpi-sub" style="color: #60A5FA;">Fatura em progresso</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kcol2:
            cor_sub = "#10B981" if saldo_cartao_restante >= 0 else "#EF4444"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Saldo Cartão Livre</div>
                <div class="kpi-value" style="color: {'#10B981' if saldo_cartao_restante >= 0 else '#EF4444'};">R$ {saldo_cartao_restante:,.2f}</div>
                <div class="kpi-sub" style="color: {cor_sub};">Meta Teto R$ {meta_fatura:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

        with kcol3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Meta Diária Limite</div>
                <div class="kpi-value" style="color: #A855F7;">R$ {meta_diaria:,.2f}</div>
                <div class="kpi-sub" style="color: #9CA3AF;">Restam {dias_restantes} dias</div>
            </div>
            """, unsafe_allow_html=True)

        with kcol4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Contas Externas</div>
                <div class="kpi-value" style="color: #F59E0B;">R$ {total_despesas_externas:,.2f}</div>
                <div class="kpi-sub" style="color: #9CA3AF;">Pix & Boletos</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Barra de Progresso Customizada
        progresso_pct = min(1.0, max(0.0, total_cartao / meta_fatura)) if meta_fatura > 0 else 1.0
        cor_barra = "#6366F1" if progresso_pct < 0.85 else "#EF4444"
        
        st.markdown(f"""
        <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 600; font-size: 0.9rem;">
                <span>Consumo da Meta do Cartão</span>
                <span>{progresso_pct*100:.1f}% ({total_cartao:,.2f} / {meta_fatura:,.2f})</span>
            </div>
            <div style="width: 100%; background-color: #1F2937; height: 10px; border-radius: 20px; overflow: hidden;">
                <div style="width: {progresso_pct*100}%; background: linear-gradient(90deg, #6366F1 0%, {cor_barra} 100%); height: 100%; border-radius: 20px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- TABS COM DESIGN MODERNO ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Linha do Tempo", 
            "🏪 Estabelecimentos", 
            "📊 Categorias", 
            "🏠 Custo Geral",
            "📋 Extrato Completo"
        ])

        # Tema padrão para os gráficos
        plotly_theme = dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9CA3AF", family="Plus Jakarta Sans"),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        with tab1:
            st.markdown("#### Evolution & Pace de Gastos")
            df_timeline = df_fatura.groupby("Data")["Valor"].sum().reset_index()
            df_timeline["Soma Acumulada"] = df_timeline["Valor"].cumsum()
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_timeline["Data"], 
                y=df_timeline["Soma Acumulada"], 
                mode='lines+markers',
                name='Acumulado',
                line=dict(color='#818CF8', width=3, shape='spline'),
                marker=dict(size=6, color='#6366F1'),
                fill='tozeroy',
                fillcolor='rgba(99, 102, 241, 0.1)'
            ))
            
            fig_line.add_hline(
                y=meta_fatura, 
                line_dash="dash", 
                line_color="#EF4444", 
                annotation_text=f" Teto Meta (R$ {meta_fatura:,.0f})",
                annotation_font_color="#EF4444"
            )

            fig_line.update_layout(**plotly_theme, height=380, xaxis_title="", yaxis_title="R$ Acumulado")
            st.plotly_chart(fig_line, use_container_width=True)

        with tab2:
            st.markdown("#### Maiores Gastos por Local")
            df_estab = df_fatura.groupby("Descrição")["Valor"].sum().sort_values(ascending=True).reset_index()
            
            fig_bar = px.bar(
                df_estab, 
                x="Valor", 
                y="Descrição", 
                orientation='h',
                text_auto='.2f',
                color="Valor",
                color_continuous_scale=["#312E81", "#6366F1", "#A855F7"]
            )
            fig_bar.update_layout(**plotly_theme, height=450, xaxis_title="Total (R$)", yaxis_title="", showlegend=False)
            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab3:
            st.markdown("#### Divisão do Cartão por Categoria")
            df_cat = df_fatura.groupby("Categoria")["Valor"].sum().reset_index()
            
            fig_pie = px.pie(
                df_cat, 
                values="Valor", 
                names="Categoria", 
                hole=0.55,
                color_discrete_sequence=["#6366F1", "#EC4899", "#10B981", "#F59E0B", "#8B5CF6", "#3B82F6"]
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(**plotly_theme, height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab4:
            st.markdown("#### Visão Geral do Mês (Cartão + Boletos)")
            dados_gerais = [
                {"Origem": "Cartão de Crédito", "Tipo": "Variável", "Valor": total_cartao},
                {"Origem": "Aluguel / Condomínio", "Tipo": "Fixa", "Valor": val_aluguel},
                {"Origem": "Luz / Energia", "Tipo": "Fixa", "Valor": val_luz},
                {"Origem": "Gás / Água", "Tipo": "Fixa", "Valor": val_gas},
                {"Origem": "Outros Boletos", "Tipo": "Fixa", "Valor": val_outros},
            ]
            df_geral = pd.DataFrame(dados_gerais)
            df_geral = df_geral[df_geral["Valor"] > 0]

            fig_geral = px.bar(
                df_geral, 
                x="Origem", 
                y="Valor", 
                color="Tipo", 
                text_auto='.2f',
                color_discrete_map={"Variável": "#6366F1", "Fixa": "#F59E0B"}
            )
            fig_geral.update_layout(**plotly_theme, height=420, xaxis_title="", yaxis_title="Total (R$)")
            st.plotly_chart(fig_geral, use_container_width=True)

        with tab5:
            st.markdown("#### Tabela de Lançamentos")
            st.dataframe(df_fatura, use_container_width=True, height=400)

    else:
        st.error("Não foi possível extrair transações deste PDF.")
else:
    st.info("👈 Faça o upload do PDF da sua fatura no painel lateral para visualizar todo o dashboard!")

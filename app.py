import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import re
import os
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="FinPulse | Controle Financeiro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ficheiro de cache para guardar o último extrato carregado
CACHE_FILE = "ultimo_extrato.csv"

# ---------------------------------------------------------
# STYLING CSS CUSTOMIZADO
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background: #0B0E14;
        color: #F3F4F6;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .header-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    .header-title {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .header-subtitle {
        color: #9CA3AF;
        font-size: 0.9rem;
        margin-top: 6px;
    }

    .kpi-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }

    .kpi-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }

    .kpi-sub {
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 4px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(17, 24, 39, 0.5);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 10px;
        padding: 0px 14px;
        color: #9CA3AF;
        font-weight: 600;
        font-size: 0.85rem;
        border: none;
        background-color: transparent;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
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
# PAINEL PRINCIPAL & LÓGICA DE PERSISTÊNCIA
# ---------------------------------------------------------
hoje = datetime.now()
dia_fechamento = 23

try:
    data_fechamento = datetime(hoje.year, hoje.month, dia_fechamento)
    if hoje > data_fechamento:
        prox_mes = hoje.month + 1 if hoje.month < 12 else 1
        prox_ano = hoje.year if hoje.month < 12 else hoje.year + 1
        data_fechamento = datetime(prox_ano, prox_mes, dia_fechamento)
except ValueError:
    data_fechamento = hoje

dias_restantes = max(0, (data_fechamento - hoje).days)

# Banner Principal
st.markdown(f"""
<div class="header-container">
    <h1 class="header-title">Controle Financeiro</h1>
    <div class="header-subtitle">Visão inteligente de gastos e metas em tempo real.</div>
    <div style="margin-top: 12px;">
        <span style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #818CF8; padding: 4px 12px; border-radius: 16px; font-size: 0.8rem; font-weight: 600;">
            📅 Fechamento: {data_fechamento.strftime('%d/%m/%Y')} ({dias_restantes} dias)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CARREGAMENTO E SESSÃO
# ---------------------------------------------------------
df_fatura = pd.DataFrame()

# Tenta carregar do cache salvo anteriormente
if os.path.exists(CACHE_FILE):
    try:
        df_fatura = pd.read_csv(CACHE_FILE)
    except Exception:
        df_fatura = pd.DataFrame()

with st.expander("📥 1. Atualizar Fatura PDF / Configurações", expanded=df_fatura.empty):
    col_up, col_cfg = st.columns([1, 1])
    
    with col_up:
        uploaded_file = st.file_uploader("Substituir / Importar Fatura PDF", type=["pdf"], key="main_pdf_uploader")
        
        # Se um novo PDF for submetido, processa e atualiza o ficheiro em cache
        if uploaded_file is not None:
            df_novo = extrair_transacoes_pdf(uploaded_file)
            if not df_novo.empty:
                df_fatura = df_novo
                df_fatura.to_csv(CACHE_FILE, index=False)
                st.success("Fatura guardada com sucesso! Ficará salva para os próximos acessos.")
                
    with col_cfg:
        meta_fatura = st.number_input("Meta Cartão (R$)", value=5000.0, step=100.0)
        corte_cabelo = st.number_input("Reserva / Agendados (R$)", value=125.0, step=10.0)

    st.markdown("---")
    st.markdown("##### 🏠 Despesas Fora do Cartão (Boletos / Pix)")
    c1, c2, c3, c4, c5 = st.columns(5)
    val_aluguel = c1.number_input("Aluguel (R$)", value=0.0, step=100.0)
    val_luz = c2.number_input("Luz (R$)", value=0.0, step=10.0)
    val_internet = c3.number_input("Internet (R$)", value=0.0, step=10.0)
    val_celular = c4.number_input("Celular (R$)", value=0.0, step=50.0)
    val_outros = c5.number_input("Outros (R$)", value=0.0, step=50.0)

total_despesas_externas = val_aluguel + val_luz + val_gas + val_outros

# ---------------------------------------------------------
# PROCESSAMENTO & EXIBIÇÃO
# ---------------------------------------------------------
if not df_fatura.empty:
    total_cartao = df_fatura["Valor"].sum()
    saldo_cartao_restante = meta_fatura - total_cartao - corte_cabelo
    meta_diaria = saldo_cartao_restante / dias_restantes if dias_restantes > 0 else 0
    total_geral_mes = total_cartao + total_despesas_externas

    # --- CARDS DE MÉTRICAS ---
    kcol1, kcol2, kcol3, kcol4 = st.columns(4)
    
    with kcol1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Cartão Acumulado</div>
            <div class="kpi-value">R$ {total_cartao:,.2f}</div>
            <div class="kpi-sub" style="color: #60A5FA;">Fatura em memória</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kcol2:
        cor_sub = "#10B981" if saldo_cartao_restante >= 0 else "#EF4444"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Saldo Cartão Livre</div>
            <div class="kpi-value" style="color: {'#10B981' if saldo_cartao_restante >= 0 else '#EF4444'};">R$ {saldo_cartao_restante:,.2f}</div>
            <div class="kpi-sub" style="color: {cor_sub};">Meta R$ {meta_fatura:,.0f}</div>
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

    # Barra de Progresso
    progresso_pct = min(1.0, max(0.0, total_cartao / meta_fatura)) if meta_fatura > 0 else 1.0
    cor_barra = "#6366F1" if progresso_pct < 0.85 else "#EF4444"
    
    st.markdown(f"""
    <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-top: 10px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-weight: 600; font-size: 0.85rem;">
            <span>Consumo da Meta</span>
            <span>{progresso_pct*100:.1f}% ({total_cartao:,.2f} / {meta_fatura:,.2f})</span>
        </div>
        <div style="width: 100%; background-color: #1F2937; height: 8px; border-radius: 20px; overflow: hidden;">
            <div style="width: {progresso_pct*100}%; background: linear-gradient(90deg, #6366F1 0%, {cor_barra} 100%); height: 100%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Linha do Tempo", 
        "🏪 Locais", 
        "📊 Categorias", 
        "🏠 Geral",
        "📋 Extrato"
    ])

    plotly_theme = dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF", family="Plus Jakarta Sans"),
        margin=dict(l=10, r=10, t=20, b=10)
    )

    with tab1:
        df_timeline = df_fatura.groupby("Data")["Valor"].sum().reset_index()
        df_timeline["Soma Acumulada"] = df_timeline["Valor"].cumsum()
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_timeline["Data"], 
            y=df_timeline["Soma Acumulada"], 
            mode='lines+markers',
            line=dict(color='#818CF8', width=3, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(99, 102, 241, 0.1)'
        ))
        fig_line.add_hline(y=meta_fatura, line_dash="dash", line_color="#EF4444")
        fig_line.update_layout(**plotly_theme, height=320)
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        df_estab = df_fatura.groupby("Descrição")["Valor"].sum().sort_values(ascending=True).reset_index()
        fig_bar = px.bar(df_estab, x="Valor", y="Descrição", orientation='h', text_auto='.2f', color="Valor", color_continuous_scale=["#312E81", "#6366F1"])
        fig_bar.update_layout(**plotly_theme, height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        df_cat = df_fatura.groupby("Categoria")["Valor"].sum().reset_index()
        fig_pie = px.pie(df_cat, values="Valor", names="Categoria", hole=0.5, color_discrete_sequence=["#6366F1", "#EC4899", "#10B981", "#F59E0B", "#8B5CF6"])
        fig_pie.update_layout(**plotly_theme, height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab4:
        dados_gerais = [
            {"Origem": "Cartão", "Tipo": "Variável", "Valor": total_cartao},
            {"Origem": "Aluguel", "Tipo": "Fixa", "Valor": val_aluguel},
            {"Origem": "Luz", "Tipo": "Fixa", "Valor": val_luz},
            {"Origem": "Gás", "Tipo": "Fixa", "Valor": val_gas},
            {"Origem": "Outros", "Tipo": "Fixa", "Valor": val_outros},
        ]
        df_geral = pd.DataFrame(dados_gerais)
        df_geral = df_geral[df_geral["Valor"] > 0]
        fig_geral = px.bar(df_geral, x="Origem", y="Valor", color="Tipo", text_auto='.2f', color_discrete_map={"Variável": "#6366F1", "Fixa": "#F59E0B"})
        fig_geral.update_layout(**plotly_theme, height=350)
        st.plotly_chart(fig_geral, use_container_width=True)

    with tab5:
        st.dataframe(df_fatura, use_container_width=True, height=350)

else:
    st.info("👈 Por favor, carregue a sua fatura em PDF na caixa acima. Ela ficará guardada automaticamente para os próximos acessos!")

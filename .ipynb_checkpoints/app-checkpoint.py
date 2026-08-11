import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3

database = "brapidados.db"

# with sqlite3.connect(database) as conn:
#         ticker_list = pd.read_sql("SELECT DISTINCT symbol FROM lista_tickers", conn)
ticker_list = ["PETR4", "VALE3", "MGLU3", "ITUB4"]
# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E CHAVE DE API
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Análise Histórica B3 - Brapi",
    page_icon="📈",
    layout="wide"
)

st.sidebar.header("Filtros de Análise")

ticker = st.sidebar.selectbox("Código do Ativo (B3):", options = ticker_list).upper()

TOKEN_BRAPI = "cdXudtXJ5wv2ALUe3JjozA"

# métricas

with sqlite3.connect(database) as conn:
    df = pd.read_sql("SELECT DISTINCT * FROM indicadores_brapi", conn)
    df2 = pd.read_sql("SELECT DISTINCT * FROM lista_tickers", conn)

df = df[df["ticker"] == ticker]
df2 = df2[df2["symbol"] == ticker]

def formatar_numero(valor):
    if pd.isna(valor) or valor == 0:
        return "R$ 0"
    
    sinal = "-" if valor < 0 else ""
    abs_val = abs(valor)
    
    if abs_val >= 1e9:
        return f"{sinal}{abs_val / 1e9:.1f}B"
    elif abs_val >= 1e6:
        return f"{sinal}{abs_val / 1e6:.1f}M"
    elif abs_val >= 1e3:
        return f"{sinal}{abs_val / 1e3:.1f}K"
    else:
        return f"{sinal}{abs_val:.0f}"

info_empresa = {
    "ticker": ticker,
    "nome": df["nome"].tolist()[0],
    "setor": df2["sector"].tolist()[0],
    "preco": df["preco"].tolist()[0],
    "variacao": 1.25,
    "market_cap": formatar_numero(df["marketcap"].tolist()[0]),
    "priceEarnings": df["priceEarnings"].tolist()[0],
    "earningsPerShare": df["earningsPerShare"].tolist()[0],
    "margem_liquida": df["margem_liquida"].tolist()[0]
}

# =============================================================================
# 1. TÍTULO E CABEÇALHO DA EMPRESA (ACIMA DAS ABAS)
# =============================================================================

url_logo = df2["logoUrl"].tolist()[0]

col_logo, col_titulo = st.columns([0.05, 0.95], vertical_alignment="center")

with col_logo:
    # Exibe a imagem a partir da URL
    st.image(url_logo, width=60)

with col_titulo:

# Linha principal do Título
    st.title(f"{info_empresa['nome']} ({info_empresa['ticker']})")
    st.caption(f"**Setor:** {info_empresa['setor']}")

# Cards de Indicadores Principais (KPIs em Destaque)
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    label="Preço da Ação", 
    value=f"R$ {info_empresa['preco']:.2f}", 
    delta=f"{info_empresa['variacao']:.2f}%"
)
col2.metric(label="Valor de Mercado", value=f"R$ {info_empresa['market_cap']}")
col3.metric(label = "Preço/Lucro", value=f"{info_empresa['priceEarnings']:.2f}")
col4.metric(label = "Lucro/Ação", value=f"R$ {info_empresa['earningsPerShare']:.2f}")
col5.metric(label = "Margem Líquida", value=f"{info_empresa['margem_liquida']*100:.0f} %")


@st.cache_data(ttl=86400)
def obter_historico_demonstrativos(ticker):
    with sqlite3.connect(database) as conn:
        df = pd.read_sql("SELECT DISTINCT * FROM indicadores_historicos WHERE symbol = ?", conn, params = (ticker,))
    return df


tab_dre, tab_candlestick, tab_balancos = st.tabs([
        "Financeiro Consolidado", 
        "🕯️ Gráfico Candlestick", 
        "📑 Histórico de Balanços e DRE"
    ])

with tab_dre:
    with sqlite3.connect(database) as conn:
        data = pd.read_sql("""SELECT endDate as Data, symbol as Symbol, totalRevenue as Revenue, ebitda as EBITDA, totalDebt as Debt,
                                grossProfits as Profits, profitMargins as profitMargin,
                                debtToEquity, returnOnAssets, returnOnEquity,
                                totalCash, totalCashPerShare, revenuePerShare
                            FROM indicadores_historicos WHERE symbol = ?""", 
                                conn, params = (ticker,))

    data["Earnings"] = data["Revenue"] * data["profitMargin"]
    # 2. Construindo a figura do Plotly
    fig = go.Figure()
    
    # Adiciona a barra de Receita
    fig.add_trace(go.Bar(
        x=data['Data'],
        y=data['Revenue'],
        name='Receita',
        marker_color='#1F77B4',
        text=[formatar_numero(v) for v in data['Revenue']],
        textposition='outside'
    ))

        # Adiciona a barra de Lucro

    fig.add_trace(go.Bar(
        x=data['Data'],
        y=data['Profits'],
        name='Lucro Bruto',
        marker_color='#1F1CB4',
        text=[formatar_numero(v) for v in data['Profits']],
        textposition='outside'
    ))
    
    # Adiciona a barra de ebtida
    fig.add_trace(go.Bar(
        x=data['Data'],
        y=data['EBITDA'],
        name='EBITDA',
        marker_color='#7F7F7F',
        text=[formatar_numero(v) for v in data['EBITDA']],
        textposition='outside'
    ))

    
    cores_lucro = [
        '#2CA02C' if val >= 0 else '#D62728' 
        for val in data['Earnings']
    ]
    fig.add_trace(go.Bar(
        x=data['Data'],
        y=data['Earnings'],
        name='Lucro Líquido',
        marker_color=cores_lucro,
        text=[formatar_numero(v) for v in data['Earnings']],
        textposition='outside'
    ))
    
    # 3. Ajustando o layout para AGRUPAR as barras (barmode='group')
    fig.update_layout(
        title='Evolução Histórica: Receita vs Lucro Bruto vs EBITDA vs Lucro Líquido',
        xaxis_title='Ano',
        yaxis_title='Valor (R$)',
        barmode='group', # Agrupa as barras lado a lado por ano
        bargap=0.15,     # Espaço entre os grupos de anos
        bargroupgap=0.1  # Espaço entre as barras do mesmo ano
    )
    st.plotly_chart(fig)

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()

        # Função para formatar os valores como porcentagem
        def formatar_pct(valor):
            if pd.isna(valor):
                return "N/A"
            return f"{valor * 100:.1f}%"  # Converte decimal (ex: 0.15) em '15.0%'

        # Linha 1: Debt to Equity
        fig.add_trace(go.Scatter(
            x=data['Data'],
            y=data['debtToEquity'],
            mode='lines+markers+text',
            name='Debt to Equity (Endividamento/PL)',
            line=dict(color='#E65100', width=3), # Laranja
            marker=dict(size=8),
            text=[formatar_pct(v) for v in data['debtToEquity']],
            textposition='top center',
            cliponaxis=False
        ))
        
        # Linha 2: Return on Equity (ROE)
        fig.add_trace(go.Scatter(
            x=data['Data'],
            y=data['returnOnEquity'],
            mode='lines+markers+text',
            name='ROE (Retorno sobre PL)',
            line=dict(color='#2E7D32', width=3), # Verde
            marker=dict(size=8),
            text=[formatar_pct(v) for v in data['returnOnEquity']],
            textposition='top center',
            cliponaxis=False
        ))
        
        # Linha 3: Return on Assets (ROA)
        fig.add_trace(go.Scatter(
            x=data['Data'],
            y=data['returnOnAssets'],
            mode='lines+markers+text',
            name='ROA (Retorno sobre Ativos)',
            line=dict(color='#1565C0', width=3), # Azul
            marker=dict(size=8),
            text=[formatar_pct(v) for v in data['returnOnAssets']],
            textposition='bottom center',
            cliponaxis=False
        ))
        
        # 3. Ajuste do Layout e Eixo Y em %
        fig.update_layout(
            title='Indicadores Financeiros Históricos (Debt/Equity, ROE e ROA)',
            xaxis_title='Ano',
            yaxis_title='Percentual / Múltiplo',
            yaxis=dict(
                tickformat='.0%', # Formata as marcações do eixo Y diretamente em %
                range=[min(min(data['returnOnEquity']), min(data['debtToEquity']), min(data['returnOnAssets'])), max(data['debtToEquity']) * 1.2] # Ajusta margem para os rótulos
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(go.Bar(
            x=data['Data'],
            y=data['totalCash'],
            name='Caixa Total',
            marker_color='#1F77B4',
            text=[formatar_numero(v) for v in data['totalCash']],
            textposition='outside'
        ))

        fig.add_trace(go.Scatter(
            x=data['Data'],
            y=data['totalCashPerShare'],
            mode='lines+markers+text',
            name='Caixa/Ação',
            line=dict(color='#E65100', width=3), # Azul
            marker=dict(size=8),
            text=[f"{x:.1f}" for x in data['totalCashPerShare']],
            textposition='bottom center',
            cliponaxis=False,
        ), secondary_y=True)


        fig.update_layout(
            title='Evolução Histórica: Caixa, Caixa/Ação',
            xaxis_title='Ano',
            yaxis_title='Caixa Total (R$)',
        )

        st.plotly_chart(fig, use_container_width=True)



st.divider()


st.caption(f"*Última atualização dos dados: 11/08/2026*")
# app_valuation_yahoo.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Valuation Brasil - Yahoo Finance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .section-header {
        color: #1f77b4;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .upside-positive {
        color: #00aa00;
        font-weight: bold;
    }
    .upside-negative {
        color: #ff4444;
        font-weight: bold;
    }
    .stock-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class YahooFinanceValuation:
    def __init__(self):
        self.acoes_brasileiras = {
            'PETR4': 'Petrobras',
            'VALE3': 'Vale',
            'ITUB4': 'Itaú Unibanco',
            'BBDC4': 'Bradesco',
            'WEGE3': 'WEG',
            'MGLU3': 'Magazine Luiza',
            'BBAS3': 'Banco do Brasil',
            'ABEV3': 'Ambev',
            'RENT3': 'Localiza',
            'B3SA3': 'B3',
            'RADL3': 'Raia Drogasil',
            'SUZB3': 'Suzano',
            'GGBR4': 'Gerdau',
            'CSNA3': 'CSN',
            'JBSS3': 'JBS',
            'LREN3': 'Lojas Renner',
            'HYPE3': 'Hypera',
            'EQTL3': 'Equatorial',
            'SBSP3': 'Sabesp'
        }
    
    def formatar_ticker(self, ticker):
        """Formata ticker para Yahoo Finance"""
        return f"{ticker}.SA"
    
    def get_dados_empresa(self, ticker):
        """Busca dados completos da empresa"""
        try:
            ticker_yf = self.formatar_ticker(ticker)
            acao = yf.Ticker(ticker_yf)
            
            # Info fundamentalista
            info = acao.info
            
            # Histórico de preços
            historico = acao.history(period="2y")
            
            # Dados formatados
            dados = {
                'ticker': ticker,
                'nome': info.get('longName', ticker),
                'setor': info.get('sector', 'N/A'),
                'industria': info.get('industry', 'N/A'),
                
                # Preços
                'preco_atual': info.get('currentPrice'),
                'variacao_dia': info.get('regularMarketChangePercent'),
                'min_52_semanas': info.get('fiftyTwoWeekLow'),
                'max_52_semanas': info.get('fiftyTwoWeekHigh'),
                
                # Múltiplos de Valuation
                'pl': info.get('trailingPE'),
                'pvp': info.get('priceToBook'),
                'psr': info.get('priceToSalesTrailing12Months'),
                'ev_ebitda': info.get('enterpriseToEbitda'),
                'ev_ebit': info.get('enterpriseToRevenue'),
                
                # Rentabilidade
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'margem_bruta': info.get('grossMargins'),
                'margem_ebit': info.get('operatingMargins'),
                'margem_liquida': info.get('profitMargins'),
                
                # Dividendos
                'dividend_yield': info.get('dividendYield'),
                'payout': info.get('payoutRatio'),
                
                # Dados por ação
                'lpa': info.get('trailingEps'),
                'vpa': info.get('bookValue'),
                'fcf_por_acao': info.get('freeCashflow', 0) / info.get('sharesOutstanding', 1),
                
                # Crescimento
                'crescimento_receita_5a': info.get('revenueGrowth'),
                'crescimento_lucro_5a': 0.10,  # Default - ajustar conforme disponível
                
                # Empresa
                'market_cap': info.get('marketCap'),
                'ebitda': info.get('ebitda'),
                'receita': info.get('totalRevenue'),
                'lucro_liquido': info.get('netIncomeToCommon'),
                
                # Histórico
                'historico': historico,
                'info_completo': info
            }
            
            return dados
            
        except Exception as e:
            st.error(f"Erro ao buscar dados de {ticker}: {str(e)}")
            return None
    
    def get_dados_setor(self, setor):
        """Busca dados médios do setor (simplificado)"""
        # Valores médios por setor (podem ser ajustados)
        medias_setor = {
            'Financeiro': {'pl': 10, 'pvp': 1.0, 'roe': 0.15},
            'Energy': {'pl': 8, 'pvp': 0.8, 'roe': 0.12},
            'Basic Materials': {'pl': 12, 'pvp': 1.2, 'roe': 0.18},
            'Industrials': {'pl': 15, 'pvp': 1.5, 'roe': 0.14},
            'Consumer Cyclical': {'pl': 18, 'pvp': 2.0, 'roe': 0.16},
            'Technology': {'pl': 25, 'pvp': 3.0, 'roe': 0.20},
            'Utilities': {'pl': 14, 'pvp': 1.1, 'roe': 0.10}
        }
        
        return medias_setor.get(setor, {'pl': 12, 'pvp': 1.2, 'roe': 0.15})
    
    def calcular_target_multiplos(self, dados_empresa, metodo, dados_setor=None):
        """Calcula target price por múltiplos"""
        lpa = dados_empresa.get('lpa', 0)
        vpa = dados_empresa.get('vpa', 0)
        preco_atual = dados_empresa.get('preco_atual', 0)
        
        if metodo == 'pl_historico':
            # Média histórica do P/L (simplificado)
            pl_historico = dados_empresa.get('pl', 12) * 0.9  # 10% abaixo do atual
            return lpa * pl_historico if lpa else None
            
        elif metodo == 'pl_setor' and dados_setor:
            pl_setor = dados_setor.get('pl', 12)
            return lpa * pl_setor if lpa else None
            
        elif metodo == 'pvp_historico':
            pvp_historico = dados_empresa.get('pvp', 1.2) * 0.95
            return vpa * pvp_historico if vpa else None
            
        elif metodo == 'pvp_setor' and dados_setor:
            pvp_setor = dados_setor.get('pvp', 1.2)
            return vpa * pvp_setor if vpa else None
            
        elif metodo == 'ev_ebitda_setor' and dados_setor:
            # Simplificação - usar múltiplo similar
            ev_ebitda_setor = 8  # Média setorial
            return preco_atual * (ev_ebitda_setor / dados_empresa.get('ev_ebitda', 8))
        
        return None
    
    def modelo_gordon(self, dados_empresa, taxa_crescimento, taxa_retorno_requerida):
        """Modelo de Gordon para valuation por dividendos"""
        dy = dados_empresa.get('dividend_yield', 0)
        preco_atual = dados_empresa.get('preco_atual', 0)
        
        if not dy or not preco_atual:
            return None
        
        dividendo_anual = preco_atual * dy
        
        if taxa_retorno_requerida <= taxa_crescimento:
            return None
        
        valor_justo = dividendo_anual / (taxa_retorno_requerida - taxa_crescimento)
        return valor_justo
    
    def fluxo_caixa_descontado(self, premisas):
        """Modelo de Fluxo de Caixa Descontado"""
        try:
            fcff_ano0 = premisas['fcff_inicial']
            crescimento_estagio1 = premisas['crescimento_estagio1'] / 100
            crescimento_estagio2 = premisas['crescimento_estagio2'] / 100
            anos_estagio1 = premisas['anos_estagio1']
            wacc = premisas['wacc'] / 100
            taxa_perpetuidade = premisas['taxa_perpetuidade'] / 100
            
            # Calcular FCFF para cada ano
            fluxos_estagio1 = []
            fcff_atual = fcff_ano0
            
            for ano in range(1, anos_estagio1 + 1):
                fcff_atual *= (1 + crescimento_estagio1)
                valor_presente = fcff_atual / ((1 + wacc) ** ano)
                fluxos_estagio1.append({
                    'ano': ano,
                    'fcff': fcff_atual,
                    'vp': valor_presente
                })
            
            # Calcular valor terminal
            fcff_terminal = fcff_atual * (1 + crescimento_estagio2)
            valor_terminal = fcff_terminal / (wacc - taxa_perpetuidade)
            valor_presente_terminal = valor_terminal / ((1 + wacc) ** anos_estagio1)
            
            # Soma todos os valores presentes
            vp_fluxos = sum([f['vp'] for f in fluxos_estagio1])
            valor_empresa = vp_fluxos + valor_presente_terminal
            
            # Ajustar para valor do equity
            divida_liquida = premisas.get('divida_liquida', 0)
            caixa_equivalentes = premisas.get('caixa_equivalentes', 0)
            valor_equity = valor_empresa - divida_liquida + caixa_equivalentes
            
            numero_acoes = premisas.get('numero_acoes', 1)
            valor_por_acao = valor_equity / numero_acoes
            
            return {
                'valor_por_acao': valor_por_acao,
                'valor_empresa': valor_empresa,
                'valor_equity': valor_equity,
                'fluxos_estagio1': fluxos_estagio1,
                'valor_terminal': valor_terminal,
                'vp_terminal': valor_presente_terminal
            }
            
        except Exception as e:
            st.error(f"Erro no cálculo FCD: {e}")
            return None

def main():
    st.markdown('<h1 class="main-header">📊 Valuation de Ações Brasileiras</h1>', unsafe_allow_html=True)
    st.markdown("**Fonte de dados: Yahoo Finance** • Desenvolvido para análise fundamentalista")
    
    # Inicializar engine
    valuation = YahooFinanceValuation()
    
    # Sidebar
    st.sidebar.header("🔍 Configurações")
    
    # Seleção da empresa
    ticker_selecionado = st.sidebar.selectbox(
        "Selecione a ação:",
        options=list(valuation.acoes_brasileiras.keys()),
        format_func=lambda x: f"{x} - {valuation.acoes_brasileiras[x]}"
    )
    
    # Buscar dados
    with st.spinner(f"Buscando dados de {ticker_selecionado}..."):
        dados_empresa = valuation.get_dados_empresa(ticker_selecionado)
    
    if not dados_empresa:
        st.error("Não foi possível carregar os dados da empresa. Tente novamente.")
        return
    
    # Header da empresa
    st.markdown(f"""
    <div class="stock-card">
        <h2>{dados_empresa['nome']} ({dados_empresa['ticker']})</h2>
        <p>📊 Setor: {dados_empresa['setor']} • 🏭 Indústria: {dados_empresa['industria']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Preço Atual", 
            f"R$ {dados_empresa['preco_atual']:.2f}" if dados_empresa['preco_atual'] else "N/A",
            f"{dados_empresa['variacao_dia']*100:.2f}%" if dados_empresa['variacao_dia'] else "N/A"
        )
    
    with col2:
        st.metric("P/L", f"{dados_empresa['pl']:.2f}" if dados_empresa['pl'] else "N/A")
    
    with col3:
        st.metric("P/VP", f"{dados_empresa['pvp']:.2f}" if dados_empresa['pvp'] else "N/A")
    
    with col4:
        dy = dados_empresa['dividend_yield']
        st.metric("Dividend Yield", f"{dy*100:.2f}%" if dy else "N/A")
    
    # Abas de análise
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Análise por Múltiplos", 
        "💰 Modelo de Gordon",
        "💸 Fluxo de Caixa Descontado",
        "📊 Dados da Empresa"
    ])
    
    with tab1:
        st.markdown('<h3 class="section-header">Valuation por Múltiplos de Mercado</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🏢 Múltiplos Atuais")
            
            metricas = [
                ("P/L", dados_empresa['pl']),
                ("P/VP", dados_empresa['pvp']),
                ("P/Sales", dados_empresa['psr']),
                ("EV/EBITDA", dados_empresa['ev_ebitda']),
                ("Dividend Yield", dados_empresa['dividend_yield']),
                ("ROE", dados_empresa['roe'])
            ]
            
            for nome, valor in metricas:
                if valor:
                    if nome in ['Dividend Yield', 'ROE']:
                        st.metric(nome, f"{valor*100:.2f}%")
                    else:
                        st.metric(nome, f"{valor:.2f}")
        
        with col2:
            st.subheader("🎯 Target Prices")
            
            # Dados do setor
            dados_setor = valuation.get_dados_setor(dados_empresa['setor'])
            
            # Calcular diferentes targets
            targets = {}
            metodos = [
                ('pl_historico', 'P/L Histórico'),
                ('pl_setor', 'P/L Setor'),
                ('pvp_historico', 'P/VP Histórico'),
                ('pvp_setor', 'P/VP Setor'),
                ('ev_ebitda_setor', 'EV/EBITDA Setor')
            ]
            
            for metodo, nome in metodos:
                target = valuation.calcular_target_multiplos(dados_empresa, metodo, dados_setor)
                if target and target > 0:
                    targets[nome] = target
            
            # Exibir targets
            preco_atual = dados_empresa['preco_atual']
            for metodo, target in targets.items():
                upside = ((target / preco_atual) - 1) * 100
                cor_classe = "upside-positive" if upside > 0 else "upside-negative"
                
                st.metric(
                    f"Target {metodo}",
                    f"R$ {target:.2f}",
                    delta=f"{upside:+.1f}%"
                )
            
            # Gráfico de comparação
            if targets:
                fig = go.Figure()
                
                # Adicionar targets
                fig.add_trace(go.Bar(
                    x=list(targets.keys()),
                    y=list(targets.values()),
                    name='Target Prices',
                    marker_color='lightblue'
                ))
                
                # Linha do preço atual
                fig.add_hline(
                    y=preco_atual,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Preço Atual: R$ {preco_atual:.2f}"
                )
                
                fig.update_layout(
                    title="Comparação de Target Prices por Múltiplos",
                    xaxis_title="Método",
                    yaxis_title="Preço (R$)",
                    showlegend=False,
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown('<h3 class="section-header">Valuation por Dividendos (Modelo de Gordon)</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚙️ Parâmetros do Modelo")
            
            taxa_crescimento = st.slider(
                "Taxa de Crescimento dos Dividendos (%)",
                min_value=0.0,
                max_value=15.0,
                value=5.0,
                step=0.1,
                help="Taxa esperada de crescimento perpetuo dos dividendos"
            )
            
            taxa_retorno_requerida = st.slider(
                "Taxa de Retorno Requerida (%)",
                min_value=5.0,
                max_value=20.0,
                value=12.0,
                step=0.1,
                help="Taxa mínima de retorno esperada pelo investidor"
            )
        
        with col2:
            st.subheader("📊 Resultado do Valuation")
            
            valor_justo = valuation.modelo_gordon(
                dados_empresa, 
                taxa_crescimento / 100,
                taxa_retorno_requerida / 100
            )
            
            if valor_justo:
                preco_atual = dados_empresa['preco_atual']
                upside = ((valor_justo / preco_atual) - 1) * 100
                
                st.metric("Valor Justo pelo Modelo de Gordon", f"R$ {valor_justo:.2f}")
                st.metric("Upside/Downside", f"{upside:+.1f}%")
                
                # Análise de sensibilidade
                st.info("**Análise de Sensibilidade:**")
                
                sens_data = []
                valores_crescimento = [taxa_crescimento-2, taxa_crescimento, taxa_crescimento+2]
                valores_retorno = [taxa_retorno_requerida-2, taxa_retorno_requerida, taxa_retorno_requerida+2]
                
                for cres in valores_crescimento:
                    for ret in valores_retorno:
                        if ret > cres and cres >= 0:
                            val = valuation.modelo_gordon(dados_empresa, cres/100, ret/100)
                            if val:
                                sens_data.append({
                                    'Crescimento': cres,
                                    'Retorno_Requerido': ret,
                                    'Valor_Justo': val
                                })
                
                if sens_data:
                    df_sens = pd.DataFrame(sens_data)
                    fig_sens = px.density_heatmap(
                        df_sens, 
                        x='Crescimento', 
                        y='Retorno_Requerido', 
                        z='Valor_Justo',
                        title='Análise de Sensibilidade - Modelo de Gordon',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_sens, use_container_width=True)
            else:
                st.warning("Não foi possível calcular o valuation pelo Modelo de Gordon. Verifique os dados de dividendos.")
    
    with tab3:
        st.markdown('<h3 class="section-header">Fluxo de Caixa Descontado (FCD)</h3>', unsafe_allow_html=True)
        
        st.subheader("⚙️ Premissas do Modelo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fcff_inicial = st.number_input(
                "FCFF Inicial (R$ milhões)",
                min_value=100.0,
                max_value=100000.0,
                value=1000.0,
                step=100.0,
                help="Fluxo de Caixa Livre para a Firma no ano 0"
            )
            
            crescimento_estagio1 = st.slider(
                "Crescimento Estágio 1 (% a.a.)",
                min_value=0.0,
                max_value=30.0,
                value=15.0,
                step=0.5,
                help="Taxa de crescimento no período de crescimento alto"
            )
            
            anos_estagio1 = st.slider(
                "Duração Estágio 1 (anos)",
                min_value=3,
                max_value=10,
                value=5,
                help="Duração do período de crescimento alto"
            )
        
        with col2:
            crescimento_estagio2 = st.slider(
                "Crescimento Estágio 2 (% a.a.)",
                min_value=0.0,
                max_value=10.0,
                value=3.0,
                step=0.1,
                help="Taxa de crescimento perpetuo após estágio 1"
            )
            
            wacc = st.slider(
                "WACC (%)",
                min_value=5.0,
                max_value=20.0,
                value=10.0,
                step=0.1,
                help="Custo Médio Ponderado de Capital"
            )
            
            taxa_perpetuidade = st.slider(
                "Taxa de Crescimento Perpétuo (%)",
                min_value=0.0,
                max_value=5.0,
                value=2.0,
                step=0.1,
                help="Taxa de crescimento final perpetuo"
            )
            
            numero_acoes = st.number_input(
                "Número de Ações (milhões)",
                min_value=1.0,
                max_value=10000.0,
                value=1000.0,
                step=10.0
            )
        
        if st.button("🎯 Calcular Valuation FCD", type="primary"):
            premisas = {
                'fcff_inicial': fcff_inicial,
                'crescimento_estagio1': crescimento_estagio1,
                'crescimento_estagio2': crescimento_estagio2,
                'anos_estagio1': anos_estagio1,
                'wacc': wacc,
                'taxa_perpetuidade': taxa_perpetuidade,
                'numero_acoes': numero_acoes,
                'divida_liquida': 0,  # Simplificação
                'caixa_equivalentes': 0  # Simplificação
            }
            
            with st.spinner("Calculando valuation..."):
                resultado = valuation.fluxo_caixa_descontado(premisas)
            
            if resultado:
                st.success("✅ Valuation calculado com sucesso!")
                
                col_res1, col_res2, col_res3 = st.columns(3)
                
                with col_res1:
                    st.metric(
                        "Valor por Ação (FCD)",
                        f"R$ {resultado['valor_por_acao']:.2f}"
                    )
                
                with col_res2:
                    st.metric(
                        "Valor da Empresa",
                        f"R$ {resultado['valor_empresa']/1e6:.2f} bi"
                    )
                
                with col_res3:
                    preco_atual = dados_empresa['preco_atual']
                    upside = ((resultado['valor_por_acao'] / preco_atual) - 1) * 100
                    st.metric("Upside/Downside FCD", f"{upside:+.1f}%")
                
                # Detalhamento do cálculo
                st.subheader("📋 Detalhamento do Cálculo")
                
                # Tabela de fluxos
                fluxos_df = pd.DataFrame(resultado['fluxos_estagio1'])
                st.write("**Fluxos de Caixa Descontados - Estágio 1:**")
                st.dataframe(fluxos_df.style.format({
                    'fcff': 'R$ {:,.0f}',
                    'vp': 'R$ {:,.0f}'
                }))
                
                st.write(f"**Valor Terminal (VP):** R$ {resultado['vp_terminal']:,.0f}")
                st.write(f"**Soma VP Fluxos:** R$ {sum([f['vp'] for f in resultado['fluxos_estagio1']]):,.0f}")
                
                # Gráfico dos fluxos
                fig_fluxos = go.Figure()
                fig_fluxos.add_trace(go.Scatter(
                    x=fluxos_df['ano'],
                    y=fluxos_df['fcff'],
                    mode='lines+markers',
                    name='FCFF Nominal',
                    line=dict(color='blue', width=3)
                ))
                fig_fluxos.add_trace(go.Scatter(
                    x=fluxos_df['ano'],
                    y=fluxos_df['vp'],
                    mode='lines+markers',
                    name='FCFF Descontado',
                    line=dict(color='green', width=3, dash='dash')
                ))
                
                fig_fluxos.update_layout(
                    title="Projeção dos Fluxos de Caixa",
                    xaxis_title="Ano",
                    yaxis_title="Valor (R$)",
                    showlegend=True,
                    height=400
                )
                
                st.plotly_chart(fig_fluxos, use_container_width=True)
    
    with tab4:
        st.markdown('<h3 class="section-header">Dados Fundamentais da Empresa</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Informações Gerais")
            info_geral = {
                'Nome': dados_empresa['nome'],
                'Setor': dados_empresa['setor'],
                'Indústria': dados_empresa['industria'],
                'Market Cap': f"R$ {dados_empresa['market_cap']/1e9:.2f} bi" if dados_empresa['market_cap'] else 'N/A',
                'Receita': f"R$ {dados_empresa['receita']/1e9:.2f} bi" if dados_empresa['receita'] else 'N/A',
                'EBITDA': f"R$ {dados_empresa['ebitda']/1e6:.2f} mi" if dados_empresa['ebitda'] else 'N/A'
            }
            
            for chave, valor in info_geral.items():
                st.write(f"**{chave}:** {valor}")
        
        with col2:
            st.subheader("💰 Rentabilidade")
            rentabilidade = {
                'ROE': f"{dados_empresa['roe']*100:.2f}%" if dados_empresa['roe'] else 'N/A',
                'ROA': f"{dados_empresa['roa']*100:.2f}%" if dados_empresa['roa'] else 'N/A',
                'Margem Líquida': f"{dados_empresa['margem_liquida']*100:.2f}%" if dados_empresa['margem_liquida'] else 'N/A',
                'Margem EBIT': f"{dados_empresa['margem_ebit']*100:.2f}%" if dados_empresa['margem_ebit'] else 'N/A',
                'LPA': f"R$ {dados_empresa['lpa']:.2f}" if dados_empresa['lpa'] else 'N/A',
                'VPA': f"R$ {dados_empresa['vpa']:.2f}" if dados_empresa['vpa'] else 'N/A'
            }
            
            for chave, valor in rentabilidade.items():
                st.write(f"**{chave}:** {valor}")
        
        # Gráfico histórico de preços
        if not dados_empresa['historico'].empty:
            st.subheader("📊 Histórico de Preços (2 anos)")
            
            fig_historico = go.Figure()
            fig_historico.add_trace(go.Scatter(
                x=dados_empresa['historico'].index,
                y=dados_empresa['historico']['Close'],
                mode='lines',
                name='Preço',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # Adicionar média móvel
            mm50 = dados_empresa['historico']['Close'].rolling(50).mean()
            fig_historico.add_trace(go.Scatter(
                x=dados_empresa['historico'].index,
                y=mm50,
                mode='lines',
                name='MM50',
                line=dict(color='orange', width=1, dash='dash')
            ))
            
            fig_historico.update_layout(
                title=f"Evolução do Preço - {dados_empresa['ticker']}",
                xaxis_title="Data",
                yaxis_title="Preço (R$)",
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig_historico, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "**💡 Aviso Legal:** Este app é para fins educacionais e de análise. "
        "As informações não constituem recomendação de investimento. "
        "Consulte um advisor financeiro antes de tomar decisões de investimento."
    )

if __name__ == "__main__":
    main()

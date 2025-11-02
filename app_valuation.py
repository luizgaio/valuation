# app_valuation_yahoo_corrigido.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuração da página DEVE SER A PRIMEIRA COISA
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
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Cache para melhor performance
@st.cache_data(ttl=3600)
def get_dados_empresa_cached(ticker):
    return get_dados_empresa(ticker)

def get_dados_empresa(ticker):
    """Busca dados completos da empresa com tratamento de erros"""
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        
        # Info fundamentalista
        info = acao.info
        
        # Histórico de preços
        historico = acao.history(period="1y")
        
        # TRATAMENTO DE DADOS PROBLEMÁTICOS
        def tratar_valor(valor, valor_max_razoavel=1000, multiplicador=1):
            """Trata valores inconsistentes do Yahoo Finance"""
            if valor is None:
                return None
            try:
                valor_float = float(valor)
                # Se for muito alto, provavelmente está em centavos ou formato errado
                if valor_float > valor_max_razoavel:
                    return valor_float * 0.01  # Converte para formato correto
                return valor_float * multiplicador
            except:
                return None
        
        # Dados corrigidos
        preco_atual = tratar_valor(info.get('currentPrice'))
        if not preco_atual and not historico.empty:
            preco_atual = historico['Close'].iloc[-1]
        
        # Dividend Yield - tratamento especial
        dy_raw = info.get('dividendYield')
        if dy_raw:
            dy = tratar_valor(dy_raw, 10, 1)  # DY não deve passar de 1000%
            if dy and dy > 10:  # Se DY > 1000%, está claramente errado
                dy = dy * 0.01  # Converte para decimal
        else:
            dy = None
        
        # VPA e LPA - tratamento especial para valores em dólar/centavos
        vpa_raw = info.get('bookValue')
        vpa = tratar_valor(vpa_raw, 100, 1)  # VPA razoável até R$ 100
        
        lpa_raw = info.get('trailingEps')
        lpa = tratar_valor(lpa_raw, 100, 1)  # LPA razoável até R$ 100
        
        # Se VPA/LPA ainda parecerem errados, calcular a partir de outros múltiplos
        if preco_atual:
            if not vpa and info.get('priceToBook'):
                vpa = preco_atual / tratar_valor(info.get('priceToBook'), 100, 1)
            
            if not lpa and info.get('trailingPE'):
                lpa = preco_atual / tratar_valor(info.get('trailingPE'), 100, 1)
        
        # P/L e P/VP - garantir que sejam razoáveis
        pl = tratar_valor(info.get('trailingPE'), 100, 1)
        pvp = tratar_valor(info.get('priceToBook'), 10, 1)
        
        # Se P/L ou P/VP estiverem absurdos, recalcular
        if preco_atual and lpa and (not pl or pl > 100):
            pl = preco_atual / lpa if lpa and lpa > 0 else None
            
        if preco_atual and vpa and (not pvp or pvp > 20):
            pvp = preco_atual / vpa if vpa and vpa > 0 else None
        
        # Dados formatados e corrigidos
        dados = {
            'ticker': ticker,
            'nome': info.get('longName', ticker),
            'setor': info.get('sector', 'N/A'),
            'industria': info.get('industry', 'N/A'),
            
            # Preços (CORRIGIDOS)
            'preco_atual': preco_atual,
            'variacao_dia': tratar_valor(info.get('regularMarketChangePercent'), 1, 1),
            'min_52_semanas': tratar_valor(info.get('fiftyTwoWeekLow'), 1000, 1),
            'max_52_semanas': tratar_valor(info.get('fiftyTwoWeekHigh'), 1000, 1),
            
            # Múltiplos de Valuation (CORRIGIDOS)
            'pl': pl,
            'pvp': pvp,
            'psr': tratar_valor(info.get('priceToSalesTrailing12Months'), 100, 1),
            'ev_ebitda': tratar_valor(info.get('enterpriseToEbitda'), 100, 1),
            
            # Rentabilidade (CORRIGIDOS)
            'roe': tratar_valor(info.get('returnOnEquity'), 10, 1),  # ROE em decimal
            'roa': tratar_valor(info.get('returnOnAssets'), 10, 1),  # ROA em decimal
            'margem_liquida': tratar_valor(info.get('profitMargins'), 1, 1),  # Margem em decimal
            
            # Dividendos (CORRIGIDOS)
            'dividend_yield': dy,
            
            # Dados por ação (CORRIGIDOS)
            'lpa': lpa,
            'vpa': vpa,
            
            # Empresa
            'market_cap': tratar_valor(info.get('marketCap'), 1e12, 1),
            'receita': tratar_valor(info.get('totalRevenue'), 1e12, 1),
            
            # Histórico
            'historico': historico,
            'info_completo': info,
            
            # Metadados para debug
            '_debug': {
                'dy_raw': dy_raw,
                'vpa_raw': vpa_raw,
                'lpa_raw': lpa_raw,
                'preco_raw': info.get('currentPrice')
            }
        }
        
        return dados
        
    except Exception as e:
        st.error(f"Erro ao buscar dados de {ticker}: {str(e)}")
        return None

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
            'EQTL3': 'Equatorial'
        }
    
    def get_dados_setor(self, setor):
        """Busca dados médios do setor (valores realistas para Brasil)"""
        medias_setor = {
            'Financial Services': {'pl': 8, 'pvp': 0.8, 'roe': 0.15},
            'Energy': {'pl': 6, 'pvp': 0.7, 'roe': 0.12},
            'Basic Materials': {'pl': 10, 'pvp': 1.0, 'roe': 0.18},
            'Industrials': {'pl': 12, 'pvp': 1.2, 'roe': 0.14},
            'Consumer Cyclical': {'pl': 15, 'pvp': 1.5, 'roe': 0.16},
            'Technology': {'pl': 20, 'pvp': 2.5, 'roe': 0.20},
            'Utilities': {'pl': 12, 'pvp': 1.0, 'roe': 0.10},
            'Healthcare': {'pl': 18, 'pvp': 2.0, 'roe': 0.16}
        }
        
        return medias_setor.get(setor, {'pl': 10, 'pvp': 1.0, 'roe': 0.15})
    
    def calcular_target_multiplos(self, dados_empresa, metodo, dados_setor=None):
        """Calcula target price por múltiplos com validação"""
        lpa = dados_empresa.get('lpa')
        vpa = dados_empresa.get('vpa')
        preco_atual = dados_empresa.get('preco_atual')
        
        if not preco_atual:
            return None
        
        # Validar se os valores são razoáveis
        def is_valor_razoavel(valor, min_val=0.01, max_val=1000):
            return valor and min_val <= valor <= max_val
        
        if metodo == 'pl_historico' and is_valor_razoavel(lpa):
            pl_historico = dados_empresa.get('pl', 10) * 0.9
            if is_valor_razoavel(pl_historico, 1, 50):
                return lpa * pl_historico
            
        elif metodo == 'pl_setor' and is_valor_razoavel(lpa) and dados_setor:
            pl_setor = dados_setor.get('pl', 10)
            if is_valor_razoavel(pl_setor, 1, 50):
                return lpa * pl_setor
            
        elif metodo == 'pvp_historico' and is_valor_razoavel(vpa):
            pvp_historico = dados_empresa.get('pvp', 1.0) * 0.95
            if is_valor_razoavel(pvp_historico, 0.1, 10):
                return vpa * pvp_historico
            
        elif metodo == 'pvp_setor' and is_valor_razoavel(vpa) and dados_setor:
            pvp_setor = dados_setor.get('pvp', 1.0)
            if is_valor_razoavel(pvp_setor, 0.1, 10):
                return vpa * pvp_setor
            
        elif metodo == 'ev_ebitda_setor':
            ev_ebitda_atual = dados_empresa.get('ev_ebitda', 6)
            if is_valor_razoavel(ev_ebitda_atual, 1, 20):
                ev_ebitda_setor = 6  # Média setorial conservadora
                return preco_atual * (ev_ebitda_setor / ev_ebitda_atual)
        
        return None
    
    def modelo_gordon(self, dados_empresa, taxa_crescimento, taxa_retorno_requerida):
        """Modelo de Gordon com validação robusta"""
        dy = dados_empresa.get('dividend_yield')
        preco_atual = dados_empresa.get('preco_atual')
        
        # Validar dados
        if not dy or not preco_atual:
            return None
        
        # Garantir que DY está em formato decimal razoável
        if dy > 1:  # Se está em percentual (ex: 17.68)
            dy = dy / 100
        
        if dy > 0.5:  # DY > 50% é irreal
            return None
        
        if taxa_retorno_requerida <= taxa_crescimento:
            return None
        
        dividendo_anual = preco_atual * dy
        valor_justo = dividendo_anual / (taxa_retorno_requerida - taxa_crescimento)
        
        # Validar se o resultado é razoável
        if valor_justo and 0.1 * preco_atual < valor_justo < 10 * preco_atual:
            return valor_justo
        
        return None
    
    def fluxo_caixa_descontado(self, premisas):
        """Modelo de Fluxo de Caixa Descontado"""
        try:
            fcff_ano0 = premisas['fcff_inicial']
            crescimento_estagio1 = premisas['crescimento_estagio1'] / 100
            crescimento_estagio2 = premisas['crescimento_estagio2'] / 100
            anos_estagio1 = premisas['anos_estagio1']
            wacc = premisas['wacc'] / 100
            taxa_perpetuidade = premisas['taxa_perpetuidade'] / 100
            
            # Validar premissas
            if wacc <= taxa_perpetuidade:
                st.error("WACC deve ser maior que a taxa de crescimento perpetuo")
                return None
            
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
            
            # Simplificação: valor equity = valor empresa
            numero_acoes = premisas.get('numero_acoes', 1)
            valor_por_acao = valor_empresa / numero_acoes
            
            return {
                'valor_por_acao': valor_por_acao,
                'valor_empresa': valor_empresa,
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
    
    # Aviso sobre dados
    st.markdown("""
    <div class="warning-box">
    ⚠️ <strong>Atenção:</strong> Os dados do Yahoo Finance para ações brasileiras podem conter inconsistências. 
    Estamos aplicando correções automáticas, mas sempre verifique com fontes oficiais.
    </div>
    """, unsafe_allow_html=True)
    
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
    with st.spinner(f"Buscando e corrigindo dados de {ticker_selecionado}..."):
        dados_empresa = get_dados_empresa_cached(ticker_selecionado)
    
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
        preco = dados_empresa['preco_atual']
        variacao = dados_empresa['variacao_dia']
        st.metric(
            "Preço Atual", 
            f"R$ {preco:.2f}" if preco else "N/A",
            f"{variacao*100:.2f}%" if variacao else "N/A"
        )
    
    with col2:
        pl = dados_empresa['pl']
        st.metric("P/L", f"{pl:.1f}" if pl else "N/A")
    
    with col3:
        pvp = dados_empresa['pvp']
        st.metric("P/VP", f"{pvp:.2f}" if pvp else "N/A")
    
    with col4:
        dy = dados_empresa['dividend_yield']
        if dy:
            # Garantir que DY está em percentual
            dy_display = dy * 100 if dy <= 1 else dy
            st.metric("Dividend Yield", f"{dy_display:.2f}%")
        else:
            st.metric("Dividend Yield", "N/A")
    
    # Debug info (opcional)
    with st.expander("🔍 Informações de Debug (Dados Crus)"):
        st.write("Dados crus do Yahoo Finance:")
        st.json(dados_empresa.get('_debug', {}))
        st.write("Dados corrigidos:")
        st.json({k: v for k, v in dados_empresa.items() if not k.startswith('_')})
    
    # Abas de análise
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Valuation por Múltiplos", 
        "💰 Modelo de Gordon",
        "💸 Fluxo de Caixa Descontado", 
        "📊 Dados da Empresa"
    ])
    
    with tab1:
        analise_multiplos(valuation, dados_empresa)
    
    with tab2:
        analise_gordon(valuation, dados_empresa)
    
    with tab3:
        analise_fcd(valuation, dados_empresa)
    
    with tab4:
        analise_dados_empresa(dados_empresa)

def analise_multiplos(valuation, dados_empresa):
    st.markdown('<h3 class="section-header">Valuation por Múltiplos de Mercado</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏢 Múltiplos Atuais")
        
        metricas = [
            ("P/L", dados_empresa['pl'], ""),
            ("P/VP", dados_empresa['pvp'], ""),
            ("P/Sales", dados_empresa['psr'], ""),
            ("EV/EBITDA", dados_empresa['ev_ebitda'], ""),
            ("Dividend Yield", dados_empresa['dividend_yield'], "%"),
            ("ROE", dados_empresa['roe'], "%")
        ]
        
        for nome, valor, sufixo in metricas:
            if valor is not None:
                if sufixo == "%":
                    display_val = valor * 100 if valor <= 1 else valor
                    st.metric(nome, f"{display_val:.2f}{sufixo}")
                else:
                    st.metric(nome, f"{valor:.2f}{sufixo}")
            else:
                st.metric(nome, "N/A")
    
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
        if preco_atual and targets:
            for metodo, target in targets.items():
                upside = ((target / preco_atual) - 1) * 100
                st.metric(
                    f"Target {metodo}",
                    f"R$ {target:.2f}",
                    delta=f"{upside:+.1f}%"
                )
            
            # Gráfico de comparação
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=list(targets.keys()),
                y=list(targets.values()),
                name='Target Prices',
                marker_color='lightblue'
            ))
            fig.add_hline(
                y=preco_atual,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Preço Atual: R$ {preco_atual:.2f}"
            )
            fig.update_layout(
                title="Comparação de Target Prices",
                xaxis_title="Método",
                yaxis_title="Preço (R$)",
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não foi possível calcular targets com os dados disponíveis.")

# ... (restante das funções analise_gordon, analise_fcd, analise_dados_empresa mantidas iguais)

if __name__ == "__main__":
    main()

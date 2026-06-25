import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import json

# Configuração da página para celular
st.set_page_config(page_title="Localizador GPS Renault", layout="wide")

st.title("🛰️ Radar de Equipamentos TI (GPS Real)")

NOME_ARQUIVO = "equipamentos.xlsx"

# 1. Carregar a planilha Excel
def carregar_dados():
    try:
        df = pd.read_excel(NOME_ARQUIVO)
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        return df.dropna(subset=['Latitude', 'Longitude'])
    except Exception as e:
        st.error(f"Erro ao ler o Excel: {e}")
        return pd.DataFrame()

df = carregar_dados()

if not df.empty:
    # --- ÁREA ADMINISTRATIVA ---
    st.sidebar.header("🔒 Área Administrativa")
    senha = st.sidebar.text_input("Senha para editar:", type="password")
    if senha == "batata":
        st.sidebar.success("Acesso liberado!")
        lista_equipamentos = df['Equipamento'].astype(str).tolist()
        equipamento_selecionado = st.sidebar.selectbox("Escolha o item:", lista_equipamentos)
        dados_atuais = df[df['Equipamento'].astype(str) == equipamento_selecionado].iloc[0]
        
        novo_nome = st.sidebar.text_input("Nome:", value=str(dados_atuais['Equipamento']))
        novo_tipo = st.sidebar.text_input("Tipo:", value=str(dados_atuais['Tipo']))
        nova_lat = st.sidebar.number_input("Lat:", value=float(dados_atuais['Latitude']), format="%.6f")
        nova_lon = st.sidebar.number_input("Lon:", value=float(dados_atuais['Longitude']), format="%.6f")
        
        if st.sidebar.button("💾 Salvar"):
            idx = df[df['Equipamento'].astype(str) == equipamento_selecionado].index[0]
            df.at[idx, 'Equipamento'] = novo_nome
            df.at[idx, 'Tipo'] = novo_tipo
            df.at[idx, 'Latitude'] = nova_lat
            df.at[idx, 'Longitude'] = nova_lon
            df.to_excel(NOME_ARQUIVO, index=False)
            st.rerun()

    # 2. Barra de busca
    busca = st.text_input("🔍 Digite o Equipamento ou Tipo para rastrear:", "")

    # Conversão segura para JSON
    dados_json = json.dumps(df[['Equipamento', 'Tipo', 'Latitude', 'Longitude']].to_dict(orient='records'))

    # --- RADAR EM JAVASCRIPT COM ESCALA DINÂMICA ---
    html_radar = f"""
    <div id="status" style="font-family: sans-serif; font-size:14px; color:#555; margin-bottom:12px;">📡 Inicializando o mapa...</div>
    <div id="debug" style="font-family: monospace; font-size:12px; color:#2563eb; margin-bottom:10px; font-weight: bold;"></div>
    
    <div style="margin-bottom: 15px; display: flex; gap: 10px;">
        <button onclick="mudarZoom(1.5)" style="flex: 1; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff;">➕ Zoom In</button>
        <button onclick="mudarZoom(0.6)" style="flex: 1; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff;">➖ Zoom Out</button>
    </div>

    <canvas id="radarCanvas" style="border:1px solid #cbd5e1; background:#f8f9fa; width:100%; height:450px; border-radius:10px;"></canvas>

    <script>
        const equipamentos = {dados_json};
        const termoBusca = "{busca}".toLowerCase().trim(); 
        
        const canvas = document.getElementById('radarCanvas');
        const ctx = canvas.getContext('2d');
        const statusDiv = document.getElementById('status');
        const debugDiv = document.getElementById('debug');

        // Ponto central padrão inicial (Renault SJP)
        let centerLat = -25.541300;
        let centerLon = -49.183700;
        let gpsAtivo = false;
        
        // Multiplicador de ajuste manual do usuário
        let modificadorZoom = 1.0; 

        function ajustarJanela() {{
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            desenharRadar(centerLat, centerLon);
        }}
        window.addEventListener('resize', ajustarJanela);
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;

        function mudarZoom(fator) {{
            modificadorZoom = modificadorZoom * fator; 
            desenharRadar(centerLat, centerLon);
        }}

        function desenharRadar(mapCenterLat, mapCenterLon) {{
            try {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                
                // 1. FILTRAR ITENS DA BUSCA ANTES DE TUDO
                const itensVisiveis = equipamentos.filter(eq => {{
                    if (termoBusca === "") return true;
                    const nomeEq = String(eq.Equipamento).toLowerCase();
                    const tipoEq = String(eq.Tipo).toLowerCase();
                    return nomeEq.includes(termoBusca) || tipoEq.includes(termoBusca);
                }});

                // 2. CALCULAR ESCALA AUTOMÁTICA PARA FORÇAR OS ITENS A APARECEREM
                let maxDist = 0.0001; // Valor mínimo para evitar divisão por zero
                itensVisiveis.forEach(eq => {{
                    const dLat = Math.abs(eq.Latitude - mapCenterLat);
                    const dLon = Math.abs(eq.Longitude - mapCenterLon);
                    if (dLat > maxDist) maxDist = dLat;
                    if (dLon > maxDist) maxDist = dLon;
                }});

                // Define a escala ideal para que o item mais distante fique na borda do canvas (com margem de 40px)
                const raioDisponivel = Math.min(centerX, centerY) - 40;
                let escalaAuto = raioDisponivel / maxDist;
                
                // Aplica o zoom manual por cima da escala automática
                let escalaFinal = escalaAuto * modificadorZoom;

                debugDiv.innerHTML = `📊 Exibindo ${{itensVisiveis.length}} itens no radar.`;

                // 3. DESENHAR ANÉIS DO RADAR
                ctx.strokeStyle = '#e2e8f0';
                ctx.lineWidth = 1.5;
                [raioDisponivel * 0.3, raioDisponivel * 0.6, raioDisponivel, raioDisponivel * 1.3].forEach(raio => {{
                    ctx.beginPath();
                    ctx.arc(centerX, centerY, raio * modificadorZoom, 0, 2 * Math.PI);
                    ctx.stroke();
                }});

                // 4. DESENHAR OS EQUIPAMENTOS COORDENADOS
                itensVisiveis.forEach(eq => {{
                    const tipoEq = String(eq.Tipo).toLowerCase();

                    // Conversão de coordenadas usando a escala inteligente recalculada
                    const dx = (eq.Longitude - mapCenterLon) * escalaFinal * Math.cos(mapCenterLat * Math.PI / 180);
                    const dy = (mapCenterLat - eq.Latitude) * escalaFinal; 

                    const x = centerX + dx;
                    const y = centerY + dy;

                    // Apenas desenha se cair dentro da área visível do Canvas
                    if (x >= 15 && x <= canvas.width - 15 && y >= 15 && y <= canvas.height - 15) {{
                        const isImpressora = tipoEq.includes('impressora') || tipoEq.includes('imp');
                        const isComputador = tipoEq.includes('computador') || tipoEq.includes('pc') || tipoEq.includes('comp');
                        
                        let corFundo = '#94a3b8'; 
                        let corBorda = '#64748b';
                        
                        if (isComputador) {{
                            corFundo = '#dcfce7'; 
                            corBorda = '#16a34a'; 
                        }} else if (isImpressora) {{
                            corFundo = '#fef9c3'; 
                            corBorda = '#ca8a04'; 
                        }}
                        
                        ctx.beginPath();
                        ctx.arc(x, y, 14, 0, 2 * Math.PI);
                        ctx.fillStyle = corFundo;
                        ctx.strokeStyle = corBorda;
                        ctx.lineWidth = 3;
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "bold 11px sans-serif";
                        ctx.fillStyle = "#1e293b";
                        ctx.strokeStyle = "#ffffff";
                        ctx.lineWidth = 3;
                        ctx.textAlign = "center";
                        ctx.strokeText(eq.Equipamento, x, y - 22);
                        ctx.fillText(eq.Equipamento, x, y - 22);
                    }}
                }});

                // 5. MARCADOR CENTRAL (Sua Posição / Fábrica)
                ctx.beginPath();
                ctx.arc(centerX, centerY, 8, 0, 2 * Math.PI);
                ctx.fillStyle = gpsAtivo ? '#2563eb' : '#f59e0b'; 
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.fill();
                ctx.stroke();

            }} catch(e) {{
                statusDiv.innerHTML = "🔴 Erro ao renderizar mapa: " + e.message;
            }}
        }}

        desenharRadar(centerLat, centerLon);

        if (navigator.geolocation) {{
            navigator.geolocation.watchPosition(
                (pos) => {{
                    gpsAtivo = true;
                    centerLat = pos.coords.latitude;
                    centerLon = pos.coords.longitude;
                    statusDiv.innerHTML = `🟢 <b>GPS Ativo</b> | Rastreando: "${{termoBusca || 'Todos'}}"`;
                    desenharRadar(centerLat, centerLon);
                }},
                (err) => {{
                    gpsAtivo = false;
                    statusDiv.innerHTML = `⚠️ Visão fixa Renault (Sem GPS) | Rastreando: "${{termoBusca || 'Todos'}}"`;
                    desenharRadar(centerLat, centerLon);
                }},
                {{ enableHighAccuracy: true, maximumAge: 0, timeout: 6000 }}
            );
        }} else {{
            statusDiv.innerHTML = "⚠️ Navegador sem suporte a GPS.";
        }}
    </script>
    """
    components.html(html_radar, height=550)

    st.markdown("### 🗺️ Legenda do Radar")
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown("🟢 **Bolinha Verde:** Computadores / PCs")
    with col2: st.markdown("🟡 **Bolinha Amarela:** Impressoras")
    with col3: st.markdown("🔵 **Bolinha Azul:** Você (Sua posição atual via GPS)")

    if busca:
        df_tabela = df[df['Equipamento'].astype(str).str.contains(busca, case=False) | df['Tipo'].astype(str).str.contains(busca, case=False)]
    else:
        df_tabela = df

    st.markdown("---")
    st.subheader(f"Lista de Equipamentos Cadastrados ({len(df_tabela)})")
    st.dataframe(df_tabela[['Equipamento', 'Tipo', 'Latitude', 'Longitude']], width="stretch")

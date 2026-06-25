import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

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
    # --- ÁREA ADMINISTRATIVA (Senha: batata) ---
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

    # 2. Barra de busca para filtrar no Radar
    busca = st.text_input("🔍 Filtrar Equipamento no Radar:", "")
    if busca:
        df_filtrado = df[df['Equipamento'].astype(str).str.contains(busca, case=False) | df['Tipo'].astype(str).str.contains(busca, case=False)]
    else:
        df_filtrado = df

    # 3. Converter dados do Excel para passar para o mapa em JavaScript
    dados_equipamentos = df_filtrado[['Equipamento', 'Tipo', 'Latitude', 'Longitude']].to_dict(orient='records')

    # --- INJEÇÃO DO MAPA DE RADAR COM GPS EM TEMPO REAL ---
    html_radar = f"""
    <div id="status" style="font-family: sans-serif; font-size:14px; color:#555; margin-bottom:10px;">📡 Aguardando sinal do GPS do celular...</div>
    
    <div style="margin-bottom: 10px;">
        <button onclick="mudarZoom(1.5)" style="padding: 8px 15px; font-size: 16px; font-weight: bold; margin-right: 5px; border-radius: 5px; border: 1px solid #ccc; background: white;">➕ Zoom</button>
        <button onclick="mudarZoom(0.6)" style="padding: 8px 15px; font-size: 16px; font-weight: bold; border-radius: 5px; border: 1px solid #ccc; background: white;">➖ Menos Zoom</button>
    </div>

    <canvas id="radarCanvas" style="border:1px solid #ccc; background:#f8f9fa; width:100%; height:450px; border-radius:10px;"></shadow>

    <script>
        const equipamentos = {str(dados_equipamentos)};
        const canvas = document.getElementById('radarCanvas');
        const ctx = canvas.getContext('2d');
        const statusDiv = document.getElementById('status');

        let ultimaLat = null;
        let ultimaLon = null;

        // Escala aumentada e calibrada para metros reais dentro do pátio industrial
        let escala = 450000; 

        function ajustarJanela() {{
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            if(ultimaLat !== null) desenharRadar(ultimaLat, ultimaLon);
        }}
        window.addEventListener('resize', ajustarJanela);
        
        // Inicializa o tamanho
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;

        function mudarZoom(fator) {{
            escala = escala * fator;
            if(ultimaLat !== null) desenharRadar(ultimaLat, ultimaLon);
        }}

        function desenharRadar(userLat, userLon) {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            
            // 1. Desenhar anéis concêntricos de distância de referência
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 1.5;
            [60, 130, 200, 270].forEach(raio => {{
                ctx.beginPath();
                ctx.arc(centerX, centerY, raio, 0, 2 * Math.PI);
                ctx.stroke();
            }});

            // 2. Desenhar os equipamentos do Excel ao redor do usuário
            equipamentos.forEach(eq => {{
                // Correção da projeção mercator local (graus para pixels com base no zoom do usuário)
                const dx = (eq.Longitude - userLon) * escala * Math.cos(userLat * Math.PI / 180);
                const dy = (userLat - eq.Latitude) * escala; 

                const x = centerX + dx;
                const y = centerY + dy;

                // Margem de segurança para desenhar o ícone inteiro na borda
                if (x >= 15 && x <= canvas.width - 15 && y >= 15 && y <= canvas.height - 15) {{
                    const isImpressora = eq.Tipo.toLowerCase().includes('impressora');
                    
                    // Fundo circular do ícone
                    ctx.beginPath();
                    ctx.arc(x, y, 16, 0, 2 * Math.PI);
                    ctx.fillStyle = isImpressora ? '#dbeafe' : '#dcfce7';
                    ctx.strokeStyle = isImpressora ? '#2563eb' : '#16a34a';
                    ctx.lineWidth = 2.5;
                    ctx.fill();
                    ctx.stroke();

                    // Emoji correspondente
                    ctx.font = "16px Arial";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText(isImpressora ? "🖨️" : "💻", x, y);

                    // Nome em caixa flutuante para facilitar leitura no sol/fábrica
                    ctx.font = "bold 10px sans-serif";
                    ctx.fillStyle = "#1e293b";
                    
                    // Sombra branca no texto para dar leitura fácil
                    ctx.strokeStyle = "#ffffff";
                    ctx.lineWidth = 3;
                    ctx.strokeText(eq.Equipamento, x, y - 24);
                    ctx.fillText(eq.Equipamento, x, y - 24);
                }}
            }});

            // 3. Desenhar marcador do Usuário (Bolinha com efeito sonar azul)
            ctx.beginPath();
            ctx.arc(centerX, centerY, 9, 0, 2 * Math.PI);
            ctx.fillStyle = '#2563eb';
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2.5;
            ctx.fill();
            ctx.stroke();
        }}

        if (navigator.geolocation) {{
            navigator.geolocation.watchPosition(
                (pos) => {{
                    ultimaLat = pos.coords.latitude;
                    ultimaLon = pos.coords.longitude;
                    statusDiv.innerHTML = `🟢 <b>GPS Conectado</b> | Lat: <b>${{ultimaLat.toFixed(6)}}</b> | Lon: <b>${{ultimaLon.toFixed(6)}}</b>`;
                    desenharRadar(ultimaLat, ultimaLon);
                }},
                (err) => {{
                    statusDiv.innerHTML = "🔴 Erro: Por favor, ative a localização/GPS de alta precisão nas configurações do celular.";
                }},
                {{ enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }}
            );
        }} else {{
            statusDiv.innerHTML = "❌ Navegador incompatível com GPS.";
        }}
    </script>
    """
    
    components.html(html_radar, height=520)

    # Tabela de conferência
    st.subheader(f"Lista de Equipamentos ({len(df_filtrado)})")
    st.dataframe(df_filtrado[['Equipamento', 'Tipo', 'Latitude', 'Longitude']], width="stretch")
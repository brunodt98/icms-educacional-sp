import folium
import pandas as pd

def gerar_mapa_calor():
    print("Gerando mapa de calor de São Paulo...")
    
    # 1. Carregar os dados que você processou
    try:
        df = pd.read_csv('data/processed/dados_finais_sp.csv')
    except FileNotFoundError:
        print("❌ Erro: Arquivo 'dados_finais_sp.csv' não encontrado. Rode o main.py primeiro.")
        return

    # 2. Criar o mapa centrado no estado de SP
    mapa = folium.Map(location=[-23.5489, -46.6388], zoom_start=7, tiles="cartodbpositron")

    # 3. Adicionar os marcadores baseados no status do ICMS/VAAR
    # Nota: No seu projeto real, você fará um merge com coordenadas do IBGE aqui
    for index, row in df.iterrows():
        # Exemplo de lógica: se houver erro no PDF (Motivo preenchido), marcador vermelho
        # Aqui assumimos que você terá as colunas 'latitude' e 'longitude' após o merge
        if 'latitude' in df.columns and 'longitude' in df.columns:
            cor = 'red' if pd.notnull(row.get('Motivo')) else 'green'
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                color=cor,
                fill=True,
                fill_opacity=0.7,
                popup=f"Município: {row.get('Ente Federado')}<br>Status: {cor}"
            ).add_to(mapa)

    # 4. Salvar o resultado
    mapa.save('output/mapa_final_sp.html')
    print("✅ Mapa gerado com sucesso em: output/mapa_final_sp.html")
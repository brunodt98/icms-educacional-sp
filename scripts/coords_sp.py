import geobr
import pandas as pd
import os

def criar_base_coordenadas():
    print("🌍 Buscando coordenadas oficiais do IBGE para todo o estado...")
    os.makedirs('data/raw', exist_ok=True)
    
    # Baixa os dados de SP (ano 2022 é o mais estável para o ICMS atual)
    df_sp = geobr.read_municipality(code_muni="SP", year=2022)
    
    # Extrai a latitude e longitude do centro de cada cidade
    df_sp['latitude'] = df_sp.geometry.centroid.y
    df_sp['longitude'] = df_sp.geometry.centroid.x
    
    # Padroniza o nome para o cruzamento
    df_sp['Município_Join'] = df_sp['name_muni'].str.upper().str.strip()
    
    df_coords = df_sp[['Município_Join', 'latitude', 'longitude']]
    df_coords.to_csv('data/raw/municipios_sp_coords.csv', index=False)
    print(f"✅ Base completa gerada: {len(df_coords)} municípios carregados.")
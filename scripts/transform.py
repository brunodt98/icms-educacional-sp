import pandas as pd

def processar_sp():
    print("⚙️ Processando dados de todos os municípios de São Paulo...")
    
    df_rec = pd.read_csv('data/processed/receitas_br.csv')
    df_ina = pd.read_csv('data/processed/inabilitados_br.csv')
    df_coords = pd.read_csv('data/raw/municipios_sp_coords.csv')

    # Limpeza de colunas
    df_rec.columns = [str(c).replace('\n', ' ').strip() for c in df_rec.columns]
    df_ina.columns = [str(c).replace('\n', ' ').strip() for c in df_ina.columns]

    # --- DESCOBRINDO A COLUNA DE MOTIVO ---
    # O PDF pode chamar de 'Motivo', 'Descrição', 'Pendência', etc.
    # Vamos pegar a última coluna do arquivo de inabilitados, que geralmente é onde está o erro
    coluna_motivo = df_ina.columns[-1] 
    print(f"🔍 Identificada coluna de restrição: {coluna_motivo}")

    # Filtrar São Paulo
    sp_receitas = df_rec[df_rec.iloc[:, 0].astype(str).str.contains('SP', na=False)].copy()
    sp_inabilitados = df_ina[df_ina.iloc[:, 0].astype(str).str.contains('SP', na=False)].copy()
    
    # Preparar as Chaves de Cruzamento
    sp_receitas['Município_Join'] = sp_receitas.iloc[:, 2].astype(str).str.upper().str.strip()
    sp_inabilitados['Município_Join'] = sp_inabilitados.iloc[:, 1].astype(str).str.upper().str.strip()
    df_coords['Município_Join'] = df_coords['Município_Join'].astype(str).str.upper().str.strip()

    # Cruzamento 1: Unir Receitas com Inabilitados
    # Renomeamos a coluna encontrada para 'Motivo' para manter o padrão
    sp_inabilitados = sp_inabilitados.rename(columns={coluna_motivo: 'Motivo'})

    df_merge_info = pd.merge(
        sp_receitas, 
        sp_inabilitados[['Município_Join', 'Motivo']], 
        on='Município_Join', 
        how='left'
    )

    # Cruzamento 2: Unir com as Coordenadas
    df_final = pd.merge(
        df_merge_info, 
        df_coords[['Município_Join', 'latitude', 'longitude']], 
        on='Município_Join', 
        how='inner'
    )

    df_final.to_csv('data/processed/dados_finais_sp.csv', index=False)
    
    total = len(df_final)
    # Conta quantos municípios têm algo escrito na coluna de Motivo
    inabilitados_count = df_final['Motivo'].dropna().count()
    
    print(f"✅ Sucesso! {total} municípios processados.")
    print(f"📊 Destes, {inabilitados_count} possuem restrições no VAAR.")

if __name__ == "__main__":
    processar_sp()
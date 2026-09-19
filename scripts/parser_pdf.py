import pdfplumber
import pandas as pd
import os

def extrair_dados():
    # Caminhos dos arquivos
    path_receitas = 'data/raw/receita-total-do-fundeb-por-ente-federado.pdf'
    path_inabilitados = 'data/raw/RedesInabilitadasVAAR20251.pdf'
    
    # 1. Extraindo Receitas (VAAR)
    with pdfplumber.open(path_receitas) as pdf:
        paginas = []
        for page in pdf.pages:
            tabela = page.extract_table()
            if tabela:
                paginas.extend(tabela)
    
    df_receitas = pd.DataFrame(paginas[1:], columns=paginas[0])
    df_receitas.to_csv('data/processed/receitas_br.csv', index=False)

    # 2. Extraindo Inabilitados
    with pdfplumber.open(path_inabilitados) as pdf:
        paginas_inab = []
        for page in pdf.pages:
            tabela = page.extract_table()
            if tabela:
                paginas_inab.extend(tabela)
                
    df_inab = pd.DataFrame(paginas_inab[1:], columns=paginas_inab[0])
    df_inab.to_csv('data/processed/inabilitados_br.csv', index=False)
    
    print("Arquivos extraídos com sucesso para data/processed/")

if __name__ == "__main__":
    extrair_dados()
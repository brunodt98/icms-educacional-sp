import sys
import os

# Ajusta o caminho para encontrar a pasta scripts
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from scripts.coords_sp import criar_base_coordenadas
from scripts.parser_pdf import extrair_dados
from scripts.transform import processar_sp
from scripts.heatmap import gerar_mapa_calor


if __name__ == "__main__":
    try:
        print("\n--- 🚀 Iniciando Pipeline ICMS Educacional SP ---")

        print("Passo 0: Configurando base de coordenadas...")
        criar_base_coordenadas()

        extrair_dados()
        processar_sp()
        gerar_mapa_calor()
        print("\n--- ✅ Tudo pronto! Verifique a pasta 'output' ---")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
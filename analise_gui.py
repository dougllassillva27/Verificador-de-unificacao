# analise_gui.py (v4.16 - Código comentado para fins didáticos)

# Seção de Importação de Bibliotecas
# Importamos as bibliotecas necessárias para a aplicação.
# customtkinter: Para criar a interface gráfica com um visual moderno.
# pyodbc: Permite a conexão com bancos de dados ODBC, como o SQL Server.
# pandas: Uma biblioteca poderosa para manipulação e análise de dados tabulares (DataFrames).
# datetime: Para obter a data e hora atual ao gerar o relatório.
# threading: Para executar tarefas de longa duração (como a análise de dados) em segundo plano,
#             evitando que a interface do usuário (GUI) congele.
# os: Para interagir com o sistema operacional, como criar pastas.
import customtkinter as ctk
import pyodbc
import pandas as pd
from datetime import datetime
import threading
import os

# Configuração Global das Tabelas
# Este dicionário mapeia um nome lógico para cada tabela do banco de dados,
# definindo o nome real da tabela e as colunas que serão extraídas.
# É uma forma de centralizar a configuração e facilitar futuras modificações.
CONFIG_TABELAS = {
    "empresas": {"tabela": "empresas", "colunas": ["id", "nome", "cnpj"]},
    "equipamentos": {"tabela": "equipamentos", "colunas": ["id", "codigo", "descricao", "serial_rep"]},
    "horarios": {"tabela": "horarios", "colunas": ["numero", "nome", "dia_semana"]},
    "funcionarios": {"tabela": "funcionarios", "colunas": ["id", "nome", "admissao", "demissao", "nascimento", "expedicao", "cpf", "n_pis", "n_folha", "n_identificador"]},
    "afastamentos": {"tabela": "afastamentos_historico", "colunas": ["id", "funcionario_id", "data_inicio", "data_fim"]},
    "funcoes": {"tabela": "funcoes", "colunas": ["id", "descricao"]},
    "departamentos": {"tabela": "departamentos", "colunas": ["id", "descricao"]}
}

def gerar_relatorio_txt(titulo, df, colunas_relatorio, arquivo_handle):
    """
    Função para gerar seções de relatório de texto a partir de um DataFrame.

    Parâmetros:
    - titulo (str): O título da seção de verificação no relatório.
    - df (DataFrame): O DataFrame do pandas contendo os dados a serem relatados.
    - colunas_relatorio (list): Lista de colunas a serem exibidas no relatório.
    - arquivo_handle (file object): O arquivo de texto onde o relatório será escrito.
    
    Retorna:
    - bool: True se dados foram escritos, False caso contrário.
    """
    # Verifica se o DataFrame não é nulo e não está vazio
    if df is not None and not df.empty:
        # Escreve o cabeçalho da seção
        arquivo_handle.write("=" * 80 + "\n")
        arquivo_handle.write(f"VERIFICAÇÃO: {titulo}\n")
        arquivo_handle.write("=" * 80 + "\n")
        
        # Garante que as colunas a serem exibidas existem no DataFrame
        colunas_existentes = [c for c in colunas_relatorio if c in df.columns]
        if not colunas_existentes: return False
        
        # Obtém a primeira coluna para usar na ordenação do relatório
        primeira_coluna_para_ordenar = colunas_existentes[0]
        
        # Remove linhas com valores nulos na coluna de ordenação
        df_limpo = df.dropna(subset=[primeira_coluna_para_ordenar])
        
        # Se ainda houver dados, ordena e escreve a tabela no arquivo
        if not df_limpo.empty:
            df_ordenado = df_limpo[colunas_existentes].sort_values(by=primeira_coluna_para_ordenar)
            arquivo_handle.write(df_ordenado.to_string(index=False))
            arquivo_handle.write("\n\n")
            return True
    return False

def extrair_dados(nome_logico, config_db, conn_str):
    """
    Extrai dados de uma tabela específica de um banco de dados SQL Server.

    Parâmetros:
    - nome_logico (str): O nome lógico da tabela (ex: "empresas").
    - config_db (dict): Dicionário com informações do banco de dados de origem.
    - conn_str (str): A string de conexão com o banco de dados.

    Retorna:
    - DataFrame: Um DataFrame do pandas com os dados da tabela.
    """
    config_tabela = CONFIG_TABELAS.get(nome_logico, {})
    if not config_tabela: return pd.DataFrame()
    tabela = config_tabela["tabela"]
    # Monta a query de forma segura, garantindo a qualificação do esquema
    colunas_str = ", ".join(f"[dbo].[{tabela}].[{c}] AS [{c}]" for c in config_tabela["colunas"])
    query = f"SELECT {colunas_str} FROM [dbo].[{tabela}];"
    
    try:
        # Usa um gerenciador de contexto 'with' para garantir que a conexão seja fechada
        with pyodbc.connect(conn_str, timeout=10) as conn:
            # Lê os dados do SQL Server diretamente para um DataFrame do pandas
            df = pd.read_sql(query, conn)
            # Adiciona uma coluna de origem para identificar de qual banco os dados vieram
            df['origem_db'] = config_db['nome_identificador']
            return df
    except Exception as e:
        # Em caso de falha, exibe uma mensagem de aviso e retorna um DataFrame vazio
        print(f"\n[AVISO] Falha ao ler '{tabela}' do banco '{config_db['nome_identificador']}'. Detalhe: {e}")
        return pd.DataFrame()

def executar_analise_completa(conexao_info, bancos_selecionados, status_callback, app_instance):
    """
    Função principal que orquestra a extração, consolidação e análise dos dados.
    Esta função é executada em uma thread separada para não travar a GUI.

    Parâmetros:
    - conexao_info (dict): Informações de servidor, usuário e senha.
    - bancos_selecionados (list): Lista de nomes dos bancos a serem analisados.
    - status_callback (function): Função para atualizar o status na GUI.
    - app_instance (App): A instância da classe da aplicação para chamar 'after()'.
    """
    try:
        # Configuração da pasta de resultados
        pasta_resultados = "Resultados_Analise"
        os.makedirs(pasta_resultados, exist_ok=True)
        caminho_relatorio = os.path.join(pasta_resultados, "relatorio_analise.txt")
        status_callback(f"Pasta de resultados: '{pasta_resultados}'")
        
        # Estruturas para armazenar dados extraídos e contagens
        todos_os_dados = {key: [] for key in CONFIG_TABELAS.keys()}
        contagem_registros = {}

        # Loop principal: itera sobre cada banco de dados selecionado
        for nome_db in bancos_selecionados:
            status_callback(f"Processando banco: {nome_db}...")
            # Monta a string de conexão para o banco atual
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={conexao_info['servidor']};DATABASE={nome_db};UID={conexao_info['usuario']};PWD={conexao_info['senha']};"
            contagem_registros[nome_db] = {}

            # Sub-loop: itera sobre cada tabela a ser analisada
            for nome_logico in CONFIG_TABELAS.keys():
                df = extrair_dados(nome_logico, {"nome_identificador": nome_db}, conn_str)
                if df is not None and not df.empty:
                    todos_os_dados[nome_logico].append(df)
                    
                    # Lógica de contagem específica para cada tabela
                    if nome_logico == "funcionarios":
                        df_copy = df.copy()
                        if 'demissao' in df_copy.columns:
                            df_copy['demissao'] = pd.to_datetime(df_copy['demissao'], errors='coerce')
                            ativos = df_copy['demissao'].isnull().sum()
                            demitidos = df_copy['demissao'].notnull().sum()
                            contagem_registros[nome_db]['funcionarios'] = {'ativos': ativos, 'demitidos': demitidos}
                        else:
                            contagem_registros[nome_db]['funcionarios'] = {'ativos': len(df_copy), 'demitidos': 0}
                    elif nome_logico == "horarios":
                        # Conta o número de horários únicos (baseado na coluna 'numero')
                        contagem_registros[nome_db][nome_logico] = df['numero'].nunique()
                    else:
                        # Para todas as outras tabelas, conta o número total de linhas
                        contagem_registros[nome_db][nome_logico] = len(df)

        status_callback("Consolidando e analisando os dados...")
        
        # Concatena todos os DataFrames extraídos para uma análise consolidada
        dados_consolidados = {
            nome: pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            for nome, dfs in todos_os_dados.items()
        }
        
        # Filtra a empresa de teste antes de realizar as verificações de duplicidade
        if "empresas" in dados_consolidados and not dados_consolidados["empresas"].empty:
            cnpj_teste = "00.000.000/0000-00"
            dados_consolidados["empresas"] = dados_consolidados["empresas"][
                dados_consolidados["empresas"]["cnpj"] != cnpj_teste
            ]

        # Início da escrita do relatório
        with open(caminho_relatorio, 'w', encoding='utf-8') as relatorio:
            relatorio.write(f"Relatório de Análise Pré-Unificação - Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            # Seção do Sumário Quantitativo
            if contagem_registros:
                relatorio.write("=" * 80 + "\nSUMÁRIO QUANTITATIVO DE REGISTROS\n" + "=" * 80 + "\n")
                
                # Tamanhos de colunas para garantir alinhamento perfeito
                TAMANHO_COLUNA_NOME_BANCO = 20
                TAMANHO_COLUNA_DADOS = 30

                # Gera o cabeçalho da tabela de sumário
                tabelas_ordenadas = sorted(list(CONFIG_TABELAS.keys()))
                header = f"{'BANCO DE DADOS':<{TAMANHO_COLUNA_NOME_BANCO}}"
                for nome_tabela in tabelas_ordenadas:
                    header += f" | {nome_tabela.upper():<{TAMANHO_COLUNA_DADOS}}"
                relatorio.write(header + "\n")
                relatorio.write("-" * len(header) + "\n")

                # Inicializa o dicionário para somar os totais de cada tabela
                totais = {nome_tabela: {'total': 0, 'ativos': 0, 'demitidos': 0} for nome_tabela in tabelas_ordenadas}

                # Escreve os dados de cada banco na tabela de sumário
                for nome_db, contagens in sorted(contagem_registros.items()):
                    linha = f"{nome_db:<{TAMANHO_COLUNA_NOME_BANCO}}"
                    for nome_tabela in tabelas_ordenadas:
                        contagem = contagens.get(nome_tabela)
                        
                        # Lógica de formatação para a coluna de funcionários
                        if nome_tabela == 'funcionarios' and isinstance(contagem, dict):
                            ativos = contagem.get('ativos', 0)
                            demitidos = contagem.get('demitidos', 0)
                            linha += f" | Ativos:{ativos}/Demitidos:{demitidos}".ljust(TAMANHO_COLUNA_DADOS + 2)
                            # Acumula o total de funcionários
                            totais[nome_tabela]['ativos'] += ativos
                            totais[nome_tabela]['demitidos'] += demitidos
                        # Lógica de formatação para as demais colunas
                        elif isinstance(contagem, (int, float)):
                            linha += f" | {contagem}".ljust(TAMANHO_COLUNA_DADOS + 2)
                            # Acumula o total para as outras tabelas
                            totais[nome_tabela]['total'] += contagem
                        else:
                            # Caso a tabela não tenha dados, preenche com 0
                            linha += " | 0".ljust(TAMANHO_COLUNA_DADOS + 2)
                    relatorio.write(linha + "\n")

                # Escreve a linha de total geral
                relatorio.write("-" * len(header) + "\n")
                linha_total = f"{'TOTAL GERAL':<{TAMANHO_COLUNA_NOME_BANCO}}"
                for nome_tabela in tabelas_ordenadas:
                    if nome_tabela == 'funcionarios':
                        total_ativos = totais[nome_tabela]['ativos']
                        total_demitidos = totais[nome_tabela]['demitidos']
                        linha_total += f" | Ativos:{total_ativos}/Demitidos:{total_demitidos}".ljust(TAMANHO_COLUNA_DADOS + 2)
                    else:
                        total = totais[nome_tabela]['total']
                        linha_total += f" | {total}".ljust(TAMANHO_COLUNA_DADOS + 2)
                relatorio.write(linha_total + "\n\n\n")

            inconsistencias_encontradas = False

            # Seção de Verificações Específicas
            # Horários com mesmo nome para códigos diferentes
            df_horarios = dados_consolidados.get("horarios")
            if df_horarios is not None and not df_horarios.empty:
                pares_unicos = df_horarios[['nome', 'numero']].drop_duplicates()
                nomes_conflitantes = pares_unicos[pares_unicos.duplicated(subset=['nome'], keep=False)]['nome'].unique()
                if len(nomes_conflitantes) > 0:
                    inconsistencias_encontradas = True
                    relatorio.write("=" * 80 + "\nVERIFICAÇÃO: Horários com mesmo Nome para Códigos (numero) Diferentes\n" + "=" * 80 + "\n")
                    for nome_conflito in sorted(nomes_conflitantes):
                        relatorio.write(f"\n--- Conflito para o Nome de Horário: '{nome_conflito}' ---\n")
                        df_conflito_filtrado = df_horarios[df_horarios['nome'] == nome_conflito]
                        relatorio.write(df_conflito_filtrado[['nome', 'numero', 'dia_semana', 'origem_db']].sort_values(by=['numero', 'dia_semana']).to_string(index=False))
                        relatorio.write("\n")
                    relatorio.write("\n")
            
            # Verificações de Duplicidade Simples (Empresas, Funções, Departamentos)
            df_empresas = dados_consolidados.get("empresas")
            verificacoes_simples = {
                "Empresas com mesmo CNPJ e Razão Social": (df_empresas, ['cnpj', 'nome'], ['cnpj', 'nome', 'origem_db']),
                "Funções com mesma Descrição": ("funcoes", ['descricao'], ['descricao', 'id', 'origem_db']),
                "Departamentos com mesma Descrição": ("departamentos", ['descricao'], ['descricao', 'id', 'origem_db'])
            }
            for titulo, (nome_df_ou_df, subset_cols, report_cols) in verificacoes_simples.items():
                # Trata a entrada como DataFrame ou nome de tabela
                if isinstance(nome_df_ou_df, pd.DataFrame):
                    df = nome_df_ou_df
                else:
                    df = dados_consolidados.get(nome_df_ou_df)

                if df is not None and not df.empty:
                    # Encontra linhas duplicadas com base no subset de colunas
                    duplicados = df[df.duplicated(subset=subset_cols, keep=False)]
                    if gerar_relatorio_txt(titulo, duplicados, report_cols, relatorio): inconsistencias_encontradas = True
            
            # Verificações de Duplicidade em Equipamentos
            df_equipamentos = dados_consolidados.get("equipamentos")
            if df_equipamentos is not None and not df_equipamentos.empty:
                # Verifica duplicidade por 'codigo'
                if 'codigo' in df_equipamentos.columns:
                    duplicados = df_equipamentos[df_equipamentos['codigo'].notna() & df_equipamentos.duplicated(subset=['codigo'], keep=False)]
                    if gerar_relatorio_txt("Equipamentos com mesmo 'codigo'", duplicados, ['codigo', 'descricao', 'origem_db'], relatorio): inconsistencias_encontradas = True
                # Verifica duplicidade por 'descricao'
                if 'descricao' in df_equipamentos.columns:
                    duplicados = df_equipamentos[df_equipamentos['descricao'].notna() & df_equipamentos.duplicated(subset=['descricao'], keep=False)]
                    if gerar_relatorio_txt("Equipamentos com mesma 'descricao'", duplicados, ['descricao', 'codigo', 'origem_db'], relatorio): inconsistencias_encontradas = True
                # Verifica duplicidade por 'serial_rep'
                if 'serial_rep' in df_equipamentos.columns:
                    duplicados = df_equipamentos[df_equipamentos['serial_rep'].notna() & df_equipamentos.duplicated(subset=['serial_rep'], keep=False)]
                    if gerar_relatorio_txt("Equipamentos com mesmo 'serial_rep'", duplicados, ['serial_rep', 'descricao', 'origem_db'], relatorio): inconsistencias_encontradas = True
            
            # Verificações de Inconsistência em Funcionários
            df_funcionarios = dados_consolidados.get("funcionarios")
            if df_funcionarios is not None and not df_funcionarios.empty:
                # Verifica duplicidade por documentos
                for col_doc in ['cpf', 'n_pis', 'n_folha', 'n_identificador']:
                    if col_doc in df_funcionarios.columns:
                        duplicados = df_funcionarios[df_funcionarios[col_doc].notna() & df_funcionarios.duplicated(subset=[col_doc], keep=False)]
                        if gerar_relatorio_txt(f"Funcionários com mesmo {col_doc.upper()}", duplicados, [col_doc, 'id', 'nome', 'origem_db'], relatorio): inconsistencias_encontradas = True
                
                # Validação de Datas (formato, range e lógica)
                df_check = df_funcionarios.copy()
                colunas_data = ['admissao', 'demissao', 'nascimento', 'expedicao']
                erros_de_data = []
                originais = {col: df_check[col] for col in colunas_data if col in df_check.columns}
                
                # Converte colunas de data para tipo datetime e trata erros
                for col in colunas_data:
                    if col in df_check.columns: df_check[col] = pd.to_datetime(df_check[col], errors='coerce')
                
                # 1. Checa formato de data inválido
                for col, original_series in originais.items():
                    formato_invalido_mask = original_series.notna() & df_check[col].isna()
                    if formato_invalido_mask.any():
                        erros = df_check[formato_invalido_mask].copy()
                        erros['motivo_erro'] = f"Formato de data inválido em '{col}' (Valor: " + original_series[formato_invalido_mask].astype(str) + ")"
                        erros_de_data.append(erros)
                
                # 2. Checa datas fora do range aceitável
                min_date, max_date = pd.Timestamp('1900-01-01'), pd.Timestamp('2079-12-31')
                for col in colunas_data:
                    if col in df_check.columns:
                        range_mask = df_check[col].notna() & ((df_check[col] < min_date) | (df_check[col] > max_date))
                        if range_mask.any():
                            erros = df_check[range_mask].copy()
                            erros['motivo_erro'] = f"Data em '{col}' fora do range (1900-2079)"
                            erros_de_data.append(erros)
                
                # 3. Checa inconsistência lógica: demissão antes da admissão
                if 'admissao' in df_check.columns and 'demissao' in df_check.columns:
                    logica_mask = df_check['admissao'].notna() & df_check['demissao'].notna() & (df_check['demissao'] < df_check['admissao'])
                    if logica_mask.any():
                        erros = df_check[logica_mask].copy()
                        erros['motivo_erro'] = "Demissão anterior à admissão"
                        erros_de_data.append(erros)
                        
                # Consolida e reporta todos os erros de data
                if erros_de_data:
                    df_final_erros = pd.concat(erros_de_data).drop_duplicates(subset=['id', 'origem_db', 'motivo_erro'])
                    if gerar_relatorio_txt("Funcionários com Inconsistências de Datas", df_final_erros, ['id', 'nome', 'admissao', 'demissao', 'nascimento', 'motivo_erro', 'origem_db'], relatorio): inconsistencias_encontradas = True
            
            # Verificação de Afastamentos Sobrepostos
            df_afastamentos = dados_consolidados.get("afastamentos")
            if df_afastamentos is not None and not df_afastamentos.empty and df_funcionarios is not None and not df_funcionarios.empty:
                 # Converte colunas de data
                 df_afastamentos['data_inicio'] = pd.to_datetime(df_afastamentos['data_inicio'], errors='coerce')
                 df_afastamentos['data_fim'] = pd.to_datetime(df_afastamentos['data_fim'], errors='coerce')
                 df_afastamentos.dropna(subset=['funcionario_id', 'data_inicio', 'data_fim'], inplace=True)
                 df_afastamentos.sort_values(['funcionario_id', 'data_inicio'], inplace=True)
                 
                 # Cria uma nova coluna com a data de fim do afastamento anterior
                 df_afastamentos['data_fim_anterior'] = df_afastamentos.groupby('funcionario_id')['data_fim'].shift(1)
                 
                 # Identifica sobreposições comparando a data de início atual com a de fim anterior
                 sobreposicoes = df_afastamentos[df_afastamentos['data_inicio'] <= df_afastamentos['data_fim_anterior']]
                 
                 # Se encontrar sobreposições, gera o relatório
                 if not sobreposicoes.empty:
                    sobreposicoes_com_nome = sobreposicoes.merge(df_funcionarios[['id', 'nome']], left_on='funcionario_id', right_on='id', how='left')
                    if gerar_relatorio_txt("Afastamentos Sobrepostos", sobreposicoes_com_nome, ['funcionario_id', 'nome', 'data_inicio', 'data_fim', 'origem_db'], relatorio): inconsistencias_encontradas = True

            # Escreve a mensagem final do relatório
            if not inconsistencias_encontradas:
                relatorio.write("NENHUMA INCONSISTÊNCIA ENCONTRADA.")
                status_callback("Análise concluída. Nenhuma inconsistência encontrada!")
            else:
                status_callback(f"Análise concluída! O relatório 'relatorio_analise.txt' foi gerado com sucesso.")
    except Exception as e:
        # Em caso de erro crítico na análise, exibe a mensagem de erro
        status_callback(f"ERRO CRÍTICO DURANTE A ANÁLISE: {e}")
    finally:
        # Garante que os botões da GUI sejam reativados após o término da análise
        app_instance.after(0, app_instance.ativar_botoes)

# Classe principal da aplicação (GUI)
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configurações da janela
        self.title("Ferramenta de Análise Pré-Unificação (v4.15)")
        self.geometry("600x750")
        ctk.set_appearance_mode("dark")
        
        # Estrutura de frames e widgets da GUI
        self.main_scrollable_frame = ctk.CTkScrollableFrame(self)
        self.main_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Seção 1: Conexão
        self.frame_conexao = ctk.CTkFrame(self.main_scrollable_frame, corner_radius=10)
        self.frame_conexao.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.frame_conexao, text="1. Conexão com o Servidor SQL", font=("", 14, "bold")).pack(pady=10)
        self.entry_servidor = ctk.CTkEntry(self.frame_conexao, placeholder_text="Servidor (ex: localhost\\SQLEXPRESS)")
        self.entry_servidor.pack(pady=5, padx=10, fill="x")
        self.entry_usuario = ctk.CTkEntry(self.frame_conexao, placeholder_text="Usuário")
        self.entry_usuario.pack(pady=5, padx=10, fill="x")
        self.entry_senha = ctk.CTkEntry(self.frame_conexao, placeholder_text="Senha", show="*")
        self.entry_senha.pack(pady=5, padx=10, fill="x")
        self.btn_conectar = ctk.CTkButton(self.frame_conexao, text="Conectar e Listar Bancos", command=self.iniciar_conexao_thread)
        self.btn_conectar.pack(pady=10, padx=10)
        
        # Seção 2: Seleção de Bancos
        self.frame_selecao = ctk.CTkFrame(self.main_scrollable_frame, corner_radius=10)
        self.frame_selecao.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.frame_selecao, text="2. Seleção dos Bancos de Dados", font=("", 14, "bold")).pack(pady=10)
        self.frame_scroll_bancos = ctk.CTkScrollableFrame(self.frame_selecao, height=150)
        self.frame_scroll_bancos.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(self.frame_scroll_bancos, text="Conecte ao servidor para listar os bancos.").pack()
        
        # Seção 3: Execução da Análise
        self.frame_execucao = ctk.CTkFrame(self.main_scrollable_frame, corner_radius=10)
        self.frame_execucao.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.frame_execucao, text="3. Executar Análise", font=("", 14, "bold")).pack(pady=10)
        self.btn_analisar = ctk.CTkButton(self.frame_execucao, text="Iniciar Análise e Gerar Relatório", command=self.iniciar_analise_thread, state="disabled")
        self.btn_analisar.pack(pady=10, padx=10)
        
        # Rótulo de Status
        self.status_label = ctk.CTkLabel(self.main_scrollable_frame, text="Aguardando conexão...", wraplength=550)
        self.status_label.pack(pady=10, padx=10)
        
        self.checkboxes_bancos = []

    def atualizar_status(self, mensagem):
        # Atualiza o rótulo de status na GUI de forma segura para threads
        self.status_label.configure(text=mensagem)

    def desativar_botoes(self):
        # Desativa os botões para evitar cliques duplos durante a execução
        self.btn_conectar.configure(state="disabled")
        self.btn_analisar.configure(state="disabled")

    def ativar_botoes(self):
        # Reativa os botões após a conclusão da tarefa
        self.btn_conectar.configure(state="normal")
        self.btn_analisar.configure(state="normal" if self.checkboxes_bancos else "disabled")

    def iniciar_conexao_thread(self):
        # Inicia a conexão em uma nova thread
        self.desativar_botoes()
        self.atualizar_status("Conectando ao servidor...")
        thread = threading.Thread(target=self.conectar_e_listar_bancos)
        thread.start()
        
    def conectar_e_listar_bancos(self):
        """Função que se conecta e lista os bancos em uma thread separada."""
        servidor, usuario, senha = self.entry_servidor.get(), self.entry_usuario.get(), self.entry_senha.get()
        if not servidor or not usuario:
            self.after(0, lambda: self.atualizar_status("Erro: Servidor e Usuário são campos obrigatórios."))
            self.after(0, self.ativar_botoes)
            return
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={servidor};DATABASE=master;UID={usuario};PWD={senha};"
        try:
            with pyodbc.connect(conn_str, timeout=5) as conn:
                cursor = conn.cursor()
                # Query para listar bancos de dados de usuário, ignorando os do sistema
                cursor.execute("SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('master', 'model', 'msdb', 'tempdb') ORDER BY name;")
                bancos = [row.name for row in cursor.fetchall()]
            
            # Limpa e preenche a lista de checkboxes na GUI
            for widget in self.frame_scroll_bancos.winfo_children(): widget.destroy()
            self.checkboxes_bancos = []
            for banco in bancos:
                checkbox = ctk.CTkCheckBox(self.frame_scroll_bancos, text=banco)
                checkbox.pack(padx=20, pady=5, anchor="w")
                self.checkboxes_bancos.append((banco, checkbox))
                
            self.after(0, lambda: self.atualizar_status("Conectado com sucesso. Selecione os bancos para análise."))
        except Exception as e:
            self.after(0, lambda e=e: self.atualizar_status(f"Falha na conexão: {e}"))
        finally:
            self.after(0, self.ativar_botoes)

    def iniciar_analise_thread(self):
        # Inicia a análise em uma nova thread
        bancos_selecionados = [banco for banco, checkbox in self.checkboxes_bancos if checkbox.get() == 1]
        if not bancos_selecionados or len(bancos_selecionados) < 2:
            self.atualizar_status("Erro: Selecione pelo menos dois bancos de dados para comparar.")
            return
        self.desativar_botoes()
        self.atualizar_status("Iniciando análise. Isso pode levar alguns minutos...")
        conexao_info = {"servidor": self.entry_servidor.get(), "usuario": self.entry_usuario.get(), "senha": self.entry_senha.get()}
        thread = threading.Thread(target=executar_analise_completa, args=(conexao_info, bancos_selecionados, lambda msg: self.after(0, lambda msg=msg: self.atualizar_status(msg)), self))
        thread.start()

# Bloco de execução principal
# Garante que o código dentro deste bloco só será executado quando o script for rodado diretamente.
if __name__ == "__main__":
    app = App()
    app.mainloop()
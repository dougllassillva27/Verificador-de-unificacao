# Verificador de unificação

## 🧰 O Que a Ferramenta Faz?

Esta aplicação desktop foi projetada para **simplificar e automatizar a verificação de múltiplos bancos de dados** do sistema _"Ponto Offline"_ (previamente convertidos para SQL Server) antes de um processo de unificação.

O objetivo principal é identificar **dados duplicados** e **inconsistências** que poderiam causar erros, sobrescrever informações ou corromper o banco de dados final.

A ferramenta:

- Conecta-se ao servidor SQL Server
- Permite a seleção de bancos a serem comparados
- Gera um **relatório de texto único** com todos os problemas encontrados

Isso permite que a equipe de suporte realize correções de forma **precisa e segura**.

---

## 🔍 Verificações Realizadas

A análise é dividida em **três categorias principais**:

### 1. Sumário Quantitativo

Para cada banco de dados, o relatório apresenta:

- Total de Funcionários **Ativos**
- Total de Funcionários **Demitidos**

---

### 2. Verificação de Dados Duplicados

Busca registros **iguais entre diferentes bancos de dados**, que poderiam gerar **conflitos de chave primária** ou **sobrescrita** de dados.

#### Campos verificados:

- **Empresas**

  - `CNPJ`
  - `Razão Social (nome)`

- **Equipamentos**

  - `Código (codigo)`
  - `Descrição (descricao)`
  - `Serial (serial_rep)`

- **Horários**

  - `Nome de horário associado a **códigos diferentes**`

- **Funções**

  - `Descrição (descricao)`

- **Departamentos**

  - `Descrição (descricao)`

- **Funcionários**
  - `CPF (cpf)`
  - `PIS (n_pis)`
  - `N° da Folha (n_folha)`
  - `N° do Identificador (n_identificador)`

---

### 3. Verificação de Integridade de Dados

#### **Funcionários (Validação de Datas)**

Ignora campos de data em branco. Valida apenas campos preenchidos com:

- **Formato Inválido**: ex: `30/02/2024`, `texto_qualquer`
- **Data Fora do Range**: fora de `01/01/1900` a `31/12/2079`
- **Inconsistência Lógica**: Data de **Demissão anterior à Admissão**

#### **Afastamentos**

- **Sobreposição**: dois ou mais afastamentos com períodos sobrepostos para o mesmo funcionário

---

## 💻 Requisitos

- Windows 10 ou superior
- Driver ODBC para SQL Server (geralmente já instalado)

---

## ⚙️ Instalação (Ambiente de Desenvolvimento)

1. Crie uma pasta e salve os arquivos `analise_gui.py` e `requirements.txt` dentro dela.

2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
.env\Scriptsctivate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## ▶️ Execução

### Para Desenvolvedores:

Com o ambiente virtual ativado:

```bash
python analise_gui.py
```

### Para Usuários Finais:

Crie um **executável `.exe`** (veja instruções abaixo).

## 📦 Criando um Executável (.exe) para Distribuição

1. Instale o **PyInstaller** (caso não tenha):

```bash
pip install pyinstaller
```

2. Use o script `.bat` de geração fornecido (automatiza tudo).

3. O executável gerado estará na pasta:

```
dist/AnalisadorDeUnificacao.exe
```

Este é o arquivo que você deve distribuir para os usuários finais.

---

## 🧑‍💻 Como Usar a Ferramenta

1. **Conexão**: Preencha os dados do SQL Server e clique em **"Conectar e Listar Bancos"**
2. **Seleção**: Marque pelo menos **dois bancos** de dados para comparar
3. **Análise**: Clique em **"Iniciar Análise e Gerar Relatório"**
4. **Resultados**: Uma pasta `Resultados_Analise` será criada com o arquivo:

```
relatorio_analise.txt
```

Esse arquivo contém:

- O sumário por banco
- Todas as inconsistências encontradas

---

## ✅ Licença

Este projeto está licenciado sob a **MIT License**.

---

# AI WhatsApp Personal Assistant

Assistente pessoal com IA para WhatsApp usando FastAPI, um gateway local
em Go com WhatsMeow e um provedor OpenAI-compatible, como Groq ou OpenAI.

O projeto recebe webhooks do gateway, processa mensagens com IA, mantem um
historico curto por contato e envia respostas de volta pelo WhatsApp.

## Estrutura

```text
.
|-- app/                    # Aplicacao FastAPI, rotas, servicos e integracoes
|   |-- api/                # Endpoints de healthcheck e webhooks
|   |-- integrations/       # Cliente do gateway e parser de payloads
|   `-- services/           # Processamento de mensagens e sessoes
|-- bot_utilities/          # Utilitarios de IA, configuracao e respostas
|-- docs/                   # Guias de ambiente e execucao
|-- gateway_go/             # Gateway WhatsApp em Go usando WhatsMeow
|-- instructions/           # Personas/instrucoes usadas pelo bot
|-- lang/                   # Arquivos de idioma herdados do bot
|-- config.yml              # Configuracoes funcionais do bot
|-- contacts.json           # Personas por contato
|-- docker-compose.yml      # Execucao com Docker Compose
|-- Dockerfile              # Imagem da aplicacao Python
|-- main.py                 # Ponto de entrada local
|-- requirements.txt        # Dependencias Python
`-- .env.example            # Modelo das variaveis de ambiente
```

## Requisitos

- Python 3.11+
- Go 1.25+ se for rodar o gateway fora do Docker
- Docker Desktop, se for usar Docker Compose
- Uma chave de API de IA compativel com OpenAI
- Opcional: Google Custom Search para busca na web

## Como configurar

1. Crie o arquivo `.env` a partir do modelo:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Preencha as variaveis do `.env`.

   Veja [docs/ENV.md](docs/ENV.md) para saber o que cada variavel faz.

3. Ajuste `config.yml` se quiser trocar modelo, idioma, gatilhos ou regras de contato.

## Rodando localmente

Em um terminal, suba a API Python:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Em outro terminal, suba o gateway:

```powershell
cd gateway_go
go mod tidy
go run main.go
```

A API sobe por padrao em `http://localhost:8000` e o gateway em
`http://localhost:3000`.

Endpoints principais:

- `GET /health`
- `POST /webhook/whatsmeow`
- `POST /webhook/whatsmeow/{event_name}`

## Rodando com Docker

```powershell
docker compose up --build
```

O `docker-compose.yml` sobe dois servicos:

- `whatsapp_gateway`: gateway WhatsMeow em Go na porta `3000`.
- `chatbot`: aplicacao FastAPI deste projeto na porta `8000`.

Na primeira execucao, acompanhe os logs do gateway e escaneie o QR Code do
WhatsApp quando ele aparecer.

```powershell
docker logs -f whatsapp-gateway-go
```

Depois de subir os containers, acesse:

- Chatbot: `http://localhost:8000`
- Healthcheck: `http://localhost:8000/health`
- Gateway: `http://localhost:3000`

## Comandos administrativos

Os numeros definidos em `ADMIN_NUMBERS` podem usar:

- `/reset`, `!reset`, `/limpar` ou `!limpar`: limpa o historico da conversa.
- `/persona nome`: altera a persona do contato atual.
- `/status` ou `!status`: mostra sessoes ativas e mensagens processadas.

## Observacoes

- Nunca versione o arquivo `.env`; ele contem segredos.
- O arquivo `.env.example` deve ficar versionado como referencia.
- Arquivos `__pycache__`, ambientes virtuais e logs sao ignorados pelo Git.

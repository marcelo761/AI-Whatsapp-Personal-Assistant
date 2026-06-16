# Variaveis de ambiente

Crie um arquivo `.env` na raiz do projeto copiando `.env.example` e preenchendo
os valores necessarios.

## IA

### `API_KEY`

Chave usada pelo cliente OpenAI-compatible.

Exemplos:

- Groq: <https://console.groq.com/keys>
- OpenAI: <https://platform.openai.com/api-keys>

Se usar OpenAI em vez de Groq, ajuste tambem `API_BASE_URL` e `MODEL_ID` no
arquivo `config.yml`.

## Busca na web

### `GOOGLE_API_KEY`

Chave da Google Custom Search JSON API.

### `GOOGLE_CSE_ID`

ID do mecanismo de busca programavel.

Essas variaveis sao opcionais. Se ficarem vazias, o bot continua respondendo,
mas a ferramenta de busca na web fica indisponivel.

## Gateway WhatsApp

### `WHATSAPP_GATEWAY_URL`

URL base do gateway Go usado pelo chatbot para enviar mensagens.

Exemplos:

```env
WHATSAPP_GATEWAY_URL=http://localhost:3000
WHATSAPP_GATEWAY_URL=http://whatsapp_gateway:3000
```

Quando rodar com Docker Compose, o `docker-compose.yml` ja define
`http://whatsapp_gateway:3000` para o container do chatbot.

### `WHATSAPP_INSTANCE`

Nome logico da instancia WhatsApp enviado no payload do webhook.

## Webhook

### `WEBHOOK_SECRET`

Token opcional para proteger o endpoint do webhook. Se preencher aqui, configure
o mesmo valor no gateway e envie no header:

```text
Authorization: Bearer seu-token
```

Se deixar vazio, o webhook nao exige esse token.

## Administracao

### `ADMIN_NUMBERS`

Numeros que podem usar comandos administrativos. Use DDI + DDD + numero, sem
sinais ou espacos, separados por virgula.

Exemplo:

```env
ADMIN_NUMBERS=5511999999999,5521988887777
```

## Servidor

### `HOST`

Endereco onde a API vai escutar. Em Docker, mantenha:

```env
HOST=0.0.0.0
```

### `PORT`

Porta HTTP da aplicacao. Padrao:

```env
PORT=8000
```

### `LOG_LEVEL`

Nivel de logs. Valores comuns:

```env
LOG_LEVEL=INFO
LOG_LEVEL=DEBUG
```

### `DEBUG`

Quando `true`, o `uvicorn` roda com reload automatico no modo local.

```env
DEBUG=false
```

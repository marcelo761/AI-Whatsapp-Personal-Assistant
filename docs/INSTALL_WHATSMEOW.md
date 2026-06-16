# Instalacao do gateway WhatsApp

Este projeto usa um gateway local em Go com WhatsMeow. O gateway recebe e envia
mensagens pelo WhatsApp e conversa com a API Python por webhook.

## Requisito

Instale o Docker Desktop para Windows:

<https://www.docker.com/products/docker-desktop/>

Depois da instalacao, abra o Docker Desktop e aguarde ele indicar que o Docker
Engine esta rodando. Em alguns computadores, o Windows pode pedir
reinicializacao ou ativacao do WSL 2.

## Subir os servicos

Na pasta do projeto, execute:

```powershell
docker compose up -d --build
```

Isso sobe:

- `whatsapp_gateway` em `http://localhost:3000`
- `chatbot` em `http://localhost:8000`

## Conectar o WhatsApp

Acompanhe os logs do gateway:

```powershell
docker logs -f whatsapp-gateway-go
```

Na primeira execucao, o gateway imprime um QR Code no terminal. Escaneie esse
QR Code pelo WhatsApp para vincular a sessao.

## Verificar logs

```powershell
docker logs whatsapp-gateway-go
docker logs ai-whatsapp-personal-assistant
```

## Parar os servicos

```powershell
docker compose down
```

## Sessao local

O arquivo `gateway_go/whatsmeow_session.db` guarda a sessao local do WhatsApp.
Nao publique esse arquivo em repositorios publicos.

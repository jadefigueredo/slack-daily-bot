# Bot Slack para Daily

Bot inteligente que armazena suas mensagens diárias e responde automaticamente à daily do Slack.

## 🚀 Características

- **Dois modos de operação**: Socket Mode (simples) e Webhook Mode (com ngrok)
- **Armazenamento automático**: Salva suas mensagens diárias em banco SQLite
- **Resposta automática**: Responde à daily usando suas mensagens do dia
- **Agendamento inteligente**: Lembra você se esquecer de responder à daily
- **Interface web**: Endpoints para monitoramento (modo webhook)

## 📋 Requisitos

- Python 3.8+
- Conta no Slack com permissões de administrador
- Ngrok (opcional, para webhook mode)

## 🛠️ Instalação

1. **Clone o repositório**
```bash
git clone <seu-repositorio>
cd bot-slack
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure o arquivo .env**
```bash
cp config_example.py .env
# Edite o arquivo .env com suas configurações
```

## 🚀 Como Executar o Projeto

### 1. Ativar a Virtual Environment
```bash
# No diretório do projeto
source slack-daily-bot/bin/activate
```

### 2. Instalar/Verificar Dependências
```bash
# Com a venv ativa
pip install -r requirements.txt
```

### 3. Executar o Bot
```bash
# Socket Mode (padrão)
python bot.py

# Ou usando o script helper
./run.sh
```

### 4. Verificar se está funcionando
- **Socket Mode**: Veja as mensagens de conexão no terminal
- **Webhook Mode**: Acesse a URL do ngrok mostrada no terminal

### 5. Desativar a venv (quando terminar)
```bash
deactivate
```

## ⚙️ Configuração do Slack App

### Método 1: Socket Mode (Recomendado para iniciantes)

1. Vá para [api.slack.com](https://api.slack.com/apps)
2. Crie um novo app "Do zero"
3. Em **OAuth & Permissions**, adicione os escopos:
   - `chat:write`
   - `channels:read`
   - `users:read`
   - `bot`
4. Instale o app no workspace
5. Em **Socket Mode**, habilite o Socket Mode
6. Crie um App-Level Token com escopo `connections:write`
7. Configure no .env:
```env
WEBHOOK_MODE=false
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### Método 2: Webhook Mode (Para desenvolvimento/produção)

1. Siga os passos 1-4 do Socket Mode
2. Em **Event Subscriptions**:
   - Habilite eventos
   - Configure Request URL: `https://seu-ngrok-url.ngrok.io/slack/events`
   - Adicione event subscription: `message.channels`
3. Configure no .env:
```env
WEBHOOK_MODE=true
USE_NGROK=true
NGROK_AUTH_TOKEN=seu-token-ngrok
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=seu-signing-secret
```

## 🔧 Configuração do Ngrok

### 1. Instalar ngrok
```bash
# Linux/Mac
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Ou baixe de: https://ngrok.com/download
```

### 2. Configurar token de autenticação
1. Crie conta em [ngrok.com](https://ngrok.com)
2. Obtenha seu token em [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken)
3. Configure no .env:
```env
NGROK_AUTH_TOKEN=seu-token-aqui
```

## 🚀 Execução Detalhada

### Socket Mode (Simples)
```bash
# 1. Ativar venv
source slack-daily-bot/bin/activate

# 2. Configure WEBHOOK_MODE=false no .env
# 3. Executar
python bot.py
```

### Webhook Mode com ngrok
```bash
# 1. Ativar venv
source slack-daily-bot/bin/activate

# 2. Configure WEBHOOK_MODE=true e USE_NGROK=true no .env
# 3. Executar
python bot.py
```

### Usando o Script Helper
```bash
# O script run.sh já ativa a venv automaticamente
chmod +x run.sh
./run.sh
```

O bot mostrará a URL do ngrok para configurar no Slack:
```
🚀 CONFIGURAÇÃO DO SLACK APP:
📝 Event Subscriptions URL: https://abc123.ngrok.io/slack/events
📊 Status do Bot: https://abc123.ngrok.io/status
💚 Health Check: https://abc123.ngrok.io/health
```

## 📊 Monitoramento (Webhook Mode)

- **Status**: `GET /status` - Informações do bot
- **Saúde**: `GET /health` - Verificação de saúde
- **Eventos**: `POST /slack/events` - Endpoint do Slack

## 🔄 Variáveis de Ambiente

### Obrigatórias (Socket Mode)
- `SLACK_BOT_TOKEN`: Token do bot
- `SLACK_APP_TOKEN`: Token do app
- `SLACK_CHANNEL_ID`: ID do canal
- `USER_ID`: Seu ID de usuário

### Obrigatórias (Webhook Mode)
- `SLACK_BOT_TOKEN`: Token do bot
- `SLACK_SIGNING_SECRET`: Signing secret
- `SLACK_CHANNEL_ID`: ID do canal
- `USER_ID`: Seu ID de usuário

### Opcionais
- `WEBHOOK_MODE`: `true/false` (default: false)
- `USE_NGROK`: `true/false` (default: false)
- `NGROK_AUTH_TOKEN`: Token do ngrok
- `PORT`: Porta do servidor (default: 3000)
- `DAILY_BOT_NAME`: Nome do bot da daily

## 📝 Como Usar

1. **Envie mensagens** durante o dia no canal configurado
2. **Aguarde a daily** - o bot responderá automaticamente
3. **Monitor**: Verifique o status em `/status` (webhook mode)
4. **Lembrete**: Às 23:55, o bot lembra se você não respondeu

## 🚨 Solução de Problemas

### Erro de importação
```bash
pip install -r requirements.txt
```

### Ngrok não funciona
1. Verifique se o token está correto
2. Teste: `ngrok http 3000`
3. Configure corretamente no Slack

### Bot não responde
1. Verifique se está no canal correto
2. Confirme o `USER_ID` e `SLACK_CHANNEL_ID`
3. Veja os logs para erros

## 📜 Logs

O bot registra todas as atividades. Monitore os logs para:
- Conexões estabelecidas
- Mensagens processadas
- Erros de configuração
- URLs do ngrok

## 🔐 Segurança

- Nunca compartilhe tokens
- Use `.env` para configurações sensíveis
- Mantenha o ngrok atualizado
- Monitore o uso da API do Slack

## ⚡ Comandos Rápidos

### Executar o Bot
```bash
# Sequência completa
source slack-daily-bot/bin/activate
python bot.py

# Ou usando o script
./run.sh
```

### Verificar Status
```bash
# Ver se a venv está ativa
which python

# Testar dependências
pip list | grep slack

# Verificar arquivo .env
cat .env
```

### Solução Rápida de Problemas
```bash
# Reinstalar dependências
source slack-daily-bot/bin/activate
pip install -r requirements.txt --force-reinstall

# Verificar se o ngrok está funcionando
curl -s https://sua-url.ngrok.io/health

# Ver logs em tempo real
tail -f messages.db
``` 
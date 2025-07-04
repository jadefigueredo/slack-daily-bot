# Exemplo de arquivo de configuração
# Copie este arquivo para .env e preencha com suas informações

# ==========================================
# CONFIGURAÇÕES BÁSICAS DO SLACK
# ==========================================

# Token do Bot Slack (encontrado na seção "OAuth & Permissions" do seu app)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Token da App Slack para Socket Mode (encontrado na seção "Basic Information")
# Necessário apenas se WEBHOOK_MODE=false
SLACK_APP_TOKEN=xapp-your-app-token-here

# Signing Secret para Webhook Mode (encontrado na seção "Basic Information")
# Necessário apenas se WEBHOOK_MODE=true
SLACK_SIGNING_SECRET=your-signing-secret-here

# ID do canal onde o bot deve operar (clique com botão direito no canal > Ver detalhes do canal)
SLACK_CHANNEL_ID=C1234567890

# Seu ID de usuário no Slack (clique no seu perfil > Mais > Copiar ID do membro)
USER_ID=U1234567890

# Nome ou parte do nome do bot que posta a daily
DAILY_BOT_NAME=daily-bot

# ==========================================
# CONFIGURAÇÕES DE MODO DE OPERAÇÃO
# ==========================================

# Modo de operação: false = Socket Mode, true = Webhook Mode
WEBHOOK_MODE=false

# Usar ngrok para expor servidor local (apenas para Webhook Mode)
USE_NGROK=false

# Token de autenticação do ngrok (opcional, mas recomendado)
# Obtenha em: https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTH_TOKEN=your-ngrok-auth-token-here

# Porta para o servidor Flask (apenas para Webhook Mode)
PORT=3000

# ==========================================
# EXEMPLOS DE CONFIGURAÇÃO
# ==========================================

# SOCKET MODE (modo padrão, mais simples):
# WEBHOOK_MODE=false
# USE_NGROK=false
# Requer: SLACK_BOT_TOKEN, SLACK_APP_TOKEN

# WEBHOOK MODE com ngrok (para desenvolvimento):
# WEBHOOK_MODE=true
# USE_NGROK=true
# NGROK_AUTH_TOKEN=your-token
# PORT=3000
# Requer: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

# WEBHOOK MODE sem ngrok (para produção):
# WEBHOOK_MODE=true
# USE_NGROK=false
# PORT=3000
# Requer: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET 
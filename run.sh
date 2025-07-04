#!/bin/bash

# Script para executar o Bot Slack
# Suporta Socket Mode e Webhook Mode com ngrok

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_blue() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    log_error "Python3 não encontrado. Instale Python 3.8 ou superior."
    exit 1
fi

# Verificar se arquivo .env existe
if [ ! -f .env ]; then
    log_warn "Arquivo .env não encontrado."
    if [ -f config_example.py ]; then
        log_info "Copiando config_example.py para .env..."
        cp config_example.py .env
        log_warn "IMPORTANTE: Edite o arquivo .env com suas configurações antes de continuar!"
        echo
        log_blue "Variáveis obrigatórias para configurar no .env:"
        echo "  - SLACK_BOT_TOKEN"
        echo "  - SLACK_CHANNEL_ID" 
        echo "  - USER_ID"
        echo
        echo "Para Socket Mode (padrão):"
        echo "  - SLACK_APP_TOKEN"
        echo
        echo "Para Webhook Mode:"
        echo "  - SLACK_SIGNING_SECRET"
        echo "  - WEBHOOK_MODE=true"
        echo
        exit 1
    else
        log_error "Arquivo config_example.py não encontrado!"
        exit 1
    fi
fi

# Carregar variáveis do .env
if [ -f .env ]; then
    source .env 2>/dev/null || true
fi

# Verificar dependências
log_info "Verificando dependências..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt > /dev/null 2>&1 || {
        log_error "Erro ao instalar dependências. Execute: pip3 install -r requirements.txt"
        exit 1
    }
    log_info "Dependências instaladas com sucesso!"
else
    log_warn "Arquivo requirements.txt não encontrado."
fi

# Determinar modo de operação
WEBHOOK_MODE=${WEBHOOK_MODE:-false}
USE_NGROK=${USE_NGROK:-false}

echo
log_blue "=========================================="
log_blue "🤖 BOT SLACK - DAILY AUTOMÁTICO"
log_blue "=========================================="

if [ "$WEBHOOK_MODE" = "true" ]; then
    log_info "Modo: WEBHOOK MODE"
    
    if [ "$USE_NGROK" = "true" ]; then
        log_info "Ngrok: HABILITADO"
        
        # Verificar se ngrok está instalado
        if ! command -v ngrok &> /dev/null; then
            log_warn "Ngrok não encontrado. Instalando..."
            
            # Tentar instalar ngrok
            if command -v apt &> /dev/null; then
                curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
                echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
                sudo apt update && sudo apt install ngrok
            else
                log_error "Instale o ngrok manualmente: https://ngrok.com/download"
                exit 1
            fi
        fi
        
        if [ -n "$NGROK_AUTH_TOKEN" ]; then
            log_info "Configurando token do ngrok..."
            ngrok config add-authtoken "$NGROK_AUTH_TOKEN" > /dev/null 2>&1 || true
        fi
    else
        log_info "Ngrok: DESABILITADO"
    fi
    
    PORT=${PORT:-3000}
    log_info "Porta: $PORT"
    
else
    log_info "Modo: SOCKET MODE"
    log_info "Ngrok: NÃO NECESSÁRIO"
fi

# Verificar configurações básicas
missing_vars=()

if [ -z "$SLACK_BOT_TOKEN" ]; then
    missing_vars+=("SLACK_BOT_TOKEN")
fi

if [ -z "$SLACK_CHANNEL_ID" ]; then
    missing_vars+=("SLACK_CHANNEL_ID")
fi

if [ -z "$USER_ID" ]; then
    missing_vars+=("USER_ID")
fi

if [ "$WEBHOOK_MODE" = "true" ]; then
    if [ -z "$SLACK_SIGNING_SECRET" ]; then
        missing_vars+=("SLACK_SIGNING_SECRET")
    fi
else
    if [ -z "$SLACK_APP_TOKEN" ]; then
        missing_vars+=("SLACK_APP_TOKEN")
    fi
fi

if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error "Variáveis obrigatórias não configuradas no .env:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo
    log_warn "Edite o arquivo .env e configure essas variáveis."
    exit 1
fi

echo
log_blue "✅ Configuração validada!"
log_info "Canal: $SLACK_CHANNEL_ID"
log_info "Usuário: $USER_ID"

if [ -n "$DAILY_BOT_NAME" ]; then
    log_info "Bot da Daily: $DAILY_BOT_NAME"
fi

echo
log_blue "🚀 Iniciando bot..."
echo

# Executar o bot
python3 bot.py 
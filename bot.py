@ -0,0 +1,658 @@
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Slack para armazenar mensagens diárias e responder à daily
"""

import os
import sqlite3
import schedule
import time
import threading
import hashlib
import hmac
from datetime import datetime, time as dt_time
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from flask import Flask, request, jsonify
from pyngrok import ngrok
import logging
import json
from typing import Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailyBot:
    def __init__(self):
        # Carregar configurações
        # self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.app_token = os.getenv('SLACK_APP_TOKEN')  # Para Socket Mode
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')  # Para Webhook Mode
        self.channel_id = os.getenv('SLACK_CHANNEL_ID')
        self.user_id = os.getenv('USER_ID')
        self.daily_bot_name = os.getenv('DAILY_BOT_NAME', 'Slackbot')
        
        # Configurações do ngrok
        self.use_ngrok = os.getenv('USE_NGROK', 'False').lower() == 'true'
        self.ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN')
        self.webhook_mode = os.getenv('WEBHOOK_MODE', 'False').lower() == 'true'
        self.port = int(os.getenv('PORT', 3000))
        
        # Validar configurações baseadas no modo
        if self.webhook_mode:
            if not all([self.bot_token, self.signing_secret, self.channel_id, self.user_id]):
                raise ValueError("Configurações obrigatórias para Webhook Mode não encontradas.")
        else:
            if not all([self.bot_token, self.app_token, self.channel_id, self.user_id]):
                raise ValueError("Configurações obrigatórias para Socket Mode não encontradas.")
        
        # Inicializar clientes Slack
        self.client = WebClient(token=self.bot_token)
        
        # Inicializar Flask app se usando webhook mode
        if self.webhook_mode:
            self.app = Flask(__name__)
            self.setup_flask_routes()
        else:
            if self.app_token:  # Verificar se app_token não é None
                self.socket_client = SocketModeClient(
                    app_token=self.app_token,
                    web_client=self.client
                )
                # Configurar handlers
                self.socket_client.socket_mode_request_listeners.append(self.process_events)
            else:
                raise ValueError("APP_TOKEN é obrigatório para Socket Mode")
        
        # Inicializar banco de dados
        self.init_database()
        
        # Variável para controlar se já respondeu à daily hoje
        self.daily_responded_today = False
        
        # URL do ngrok (será definida quando iniciado)
        self.ngrok_url: Optional[str] = None
        
    def init_database(self):
        """Inicializar banco de dados SQLite"""
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Tabela para armazenar mensagens diárias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela para controlar respostas à daily
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                response_sent BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso")
    
    def verify_slack_signature(self, request_body, timestamp, signature):
        """Verificar assinatura do Slack para webhook"""
        if not self.signing_secret:
            return False
            
        # Criar string de verificação
        sig_basestring = f'v0:{timestamp}:{request_body.decode("utf-8")}'
        
        # Criar hash HMAC
        my_signature = 'v0=' + hmac.new(
            self.signing_secret.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Comparar assinaturas
        return hmac.compare_digest(my_signature, signature)
    
    def setup_flask_routes(self):
        """Configurar rotas Flask para webhook mode"""
        
        @self.app.route('/events', methods=['POST'])
        def slack_events():
            """Endpoint para receber eventos do Slack"""
            try:
                # Log da requisição recebida
                logger.info("Requisição recebida no /events")
                logger.info(f"Headers: {dict(request.headers)}")
                
                # Obter dados brutos da requisição
                raw_body = request.get_data()
                timestamp = request.headers.get('X-Slack-Request-Timestamp')
                signature = request.headers.get('X-Slack-Signature')
                
                logger.info(f"Body size: {len(raw_body)}, Timestamp: {timestamp}")
                logger.info(f"Body content: {raw_body.decode('utf-8')[:200]}...")
                
                # Verificar assinatura (apenas se não for challenge)
                try:
                    event_data = json.loads(raw_body.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON: {e}")
                    return jsonify({'error': 'Invalid JSON'}), 400
                
                # Verificar URL challenge (configuração inicial)
                if 'challenge' in event_data:
                    logger.info("Challenge recebido, retornando challenge")
                    return jsonify({'challenge': event_data['challenge']})
                
                # Validar assinatura para eventos reais
                if not self.verify_slack_signature(raw_body, timestamp, signature):
                    logger.error("Assinatura inválida!")
                    return jsonify({'error': 'Invalid signature'}), 401
                
                logger.info("Assinatura válida, processando evento")
                logger.info(f"Evento completo: {json.dumps(event_data, indent=2)}")
                
                # Processar evento
                if 'event' in event_data:
                    event = event_data['event']
                    logger.info(f"Tipo do evento: {event.get('type')}")
                    logger.info(f"Detalhes do evento: {event}")
                    
                    if event.get('type') == 'message':
                        self.handle_message(event)
                    else:
                        logger.info(f"Evento ignorado: {event.get('type')}")
                
                return jsonify({'status': 'ok'})
                
            except Exception as e:
                logger.error(f"Erro no endpoint /events: {e}")
                logger.error(f"Traceback: ", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Endpoint para verificação de saúde"""
            return jsonify({
                'status': 'ok',
                'mode': 'webhook' if self.webhook_mode else 'socket',
                'ngrok_url': self.ngrok_url,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/status', methods=['GET'])
        def status():
            """Endpoint para verificar status do bot"""
            today = datetime.now().date().isoformat()
            messages = self.get_today_messages()
            
            return jsonify({
                'date': today,
                'messages_today': len(messages),
                'daily_responded': self.daily_responded_today,
                'mode': 'webhook' if self.webhook_mode else 'socket',
                'ngrok_url': self.ngrok_url,
                'config': {
                    'channel_id': self.channel_id,
                    'user_id': self.user_id,
                    'webhook_mode': self.webhook_mode,
                    'use_ngrok': self.use_ngrok
                }
            })
        
        @self.app.route('/debug', methods=['GET'])
        def debug():
            """Endpoint para debug de configuração"""
            return jsonify({
                'webhook_url': f"{self.ngrok_url}/events" if self.ngrok_url else "N/A",
                'status_url': f"{self.ngrok_url}/status" if self.ngrok_url else "N/A",
                'config': {
                    'SLACK_BOT_TOKEN': 'Configurado' if self.bot_token else 'Não configurado',
                    'SLACK_SIGNING_SECRET': 'Configurado' if self.signing_secret else 'Não configurado',
                    'SLACK_CHANNEL_ID': self.channel_id,
                    'USER_ID': self.user_id,
                    'WEBHOOK_MODE': self.webhook_mode,
                    'USE_NGROK': self.use_ngrok,
                    'PORT': self.port
                },
                'instructions': {
                    'step1': 'Configure no Slack App → Event Subscriptions',
                    'step2': f'Request URL: {self.ngrok_url}/events',
                    'step3': 'Subscribe to bot events: message.channels',
                    'step4': 'Reinstall app no workspace'
                }
            })
        
        @self.app.route('/test', methods=['POST'])
        def test():
            """Endpoint para testar recebimento de dados"""
            logger.info("=== ENDPOINT DE TESTE ===")
            logger.info(f"Headers: {dict(request.headers)}")
            logger.info(f"Body: {request.get_data()}")
            
            return jsonify({'status': 'test_ok', 'received': True})
    
    def setup_ngrok(self):
        """Configurar e iniciar túnel ngrok"""
        try:
            # Autenticar se token fornecido
            if self.ngrok_auth_token:
                ngrok.set_auth_token(self.ngrok_auth_token)
            
            # Criar túnel HTTP - converter port para string
            public_url = ngrok.connect(str(self.port))
            self.ngrok_url = str(public_url)
            
            logger.info(f"Túnel ngrok criado: {self.ngrok_url}")
            logger.info(f"URL do webhook: {self.ngrok_url}/events")
            logger.info(f"Status do bot: {self.ngrok_url}/status")
            
            return self.ngrok_url
            
        except Exception as e:
            logger.error(f"Erro ao configurar ngrok: {e}")
            return None
    
    def process_events(self, client, req):
        """Processar eventos do Slack"""
        try:
            if req.type == "events_api":
                event = req.payload.get("event", {})
                
                # Processar mensagens
                if event.get("type") == "message":
                    self.handle_message(event)
                    
            # Sempre responder ao Slack para confirmar recebimento
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}")
    
    def handle_message(self, event):
        """Processar mensagens recebidas"""
        try:
            logger.info(f"=== PROCESSANDO MENSAGEM ===")
            logger.info(f"Evento completo: {event}")
            
            # Log detalhado dos campos importantes
            user_id = event.get("user")
            bot_id = event.get("bot_id")
            channel = event.get("channel", "")
            text = event.get("text", "")
            
            logger.info(f"User: {user_id}, Bot: {bot_id}, Channel: {channel}")
            logger.info(f"Text: {text[:100]}...")
            logger.info(f"User configurado: {self.user_id}")
            logger.info(f"Canal configurado: {self.channel_id}")
            
            # Ignorar mensagens do próprio bot
            if bot_id:
                logger.info(f"Mensagem de bot detectada: {bot_id}")
                try:
                    # Verificar se é mensagem do bot da daily
                    bot_info = self.client.bots_info(bot=bot_id)
                    if (bot_info and 
                        isinstance(bot_info, dict) and 
                        "bot" in bot_info and 
                        isinstance(bot_info["bot"], dict) and
                        "name" in bot_info["bot"]):
                        bot_name = bot_info["bot"]["name"].lower()
                        logger.info(f"Nome do bot: {bot_name}")
                        
                        if self.daily_bot_name.lower() in bot_name:
                            logger.info("Bot da daily detectado, processando...")
                            self.handle_daily_message(event)
                        else:
                            logger.info(f"Bot ignorado: {bot_name}")
                    else:
                        logger.info("Informações do bot não disponíveis")
                except Exception as e:
                    logger.error(f"Erro ao verificar bot info: {e}")
                return
            
            # Processar mensagens do usuário configurado (canal específico ou DM direto)
            if user_id == self.user_id:
                logger.info("Usuário correto detectado!")
                
                # Aceitar mensagens do canal configurado ou DM direto com o bot
                if channel == self.channel_id:
                    logger.info("Mensagem do canal configurado")
                    self.store_user_message(text)
                    logger.info(f"Mensagem processada do canal: {channel}")
                elif channel.startswith("D"):
                    logger.info("Mensagem de DM direto")
                    self.store_user_message(text)
                    logger.info(f"Mensagem processada do DM: {channel}")
                else:
                    logger.info(f"Canal ignorado: {channel} (não é {self.channel_id} nem DM)")
            else:
                logger.info(f"Usuário ignorado: {user_id} (não é {self.user_id})")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            logger.error(f"Traceback: ", exc_info=True)
    
    def handle_daily_message(self, event):
        """Processar mensagem da daily e responder automaticamente"""
        try:
            today = datetime.now().date().isoformat()
            
            # Verificar se já respondeu hoje
            if self.daily_responded_today:
                return
                
            # Buscar mensagens do usuário para hoje
            messages = self.get_today_messages()
            
            if messages:
                # Criar resposta baseada nas mensagens do dia
                response = self.create_daily_response(messages)
                
                # Responder na thread da daily
                if self.channel_id:
                    self.client.chat_postMessage(
                        channel=self.channel_id,
                        thread_ts=event.get("ts"),
                        text=response
                    )
                
                # Marcar como respondido
                self.mark_daily_as_responded(today)
                self.daily_responded_today = True
                
                logger.info(f"Resposta à daily enviada para {today}")
            
        except Exception as e:
            logger.error(f"Erro ao responder à daily: {e}")
    
    def store_user_message(self, message):
        """Armazenar mensagem do usuário no banco"""
        logger.info(f"=== ARMAZENANDO MENSAGEM ===")
        logger.info(f"Mensagem recebida: '{message}'")
        
        if not message.strip():
            logger.warning("Mensagem vazia, ignorando")
            return
            
        today = datetime.now().date().isoformat()
        logger.info(f"Data atual: {today}")
        
        try:
            conn = sqlite3.connect('messages.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO daily_messages (date, message) VALUES (?, ?)",
                (today, message)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Mensagem armazenada para {today}: {message[:50]}...")
            
            # Enviar confirmação no DM
            logger.info("Enviando confirmação no DM...")
            self.send_dm_confirmation()
            
        except Exception as e:
            logger.error(f"Erro ao armazenar mensagem: {e}")
            logger.error(f"Traceback: ", exc_info=True)
    
    def send_dm_confirmation(self):
        """Enviar confirmação no DM mostrando como ficará a daily"""
        try:
            logger.info("=== ENVIANDO CONFIRMAÇÃO DM ===")
            
            # Buscar todas as mensagens do dia atual
            messages = self.get_today_messages()
            logger.info(f"Mensagens encontradas: {len(messages)}")
            logger.info(f"Mensagens: {messages}")
            
            if messages:
                daily_content = self.create_daily_response(messages)
                logger.info(f"Conteúdo da daily: '{daily_content}'")
                
                # Montar mensagem de confirmação
                confirmation = f"Beleza <@{self.user_id}>!\n\nEssa será sua daily de hoje:\n{daily_content}"
                logger.info(f"Mensagem de confirmação: '{confirmation}'")
                
                # Enviar no DM (canal direto com o usuário)
                logger.info(f"Enviando DM para usuário: {self.user_id}")
                if self.user_id:
                    response = self.client.chat_postMessage(
                        channel=self.user_id,  # Enviar DM direto para o usuário
                        text=confirmation
                    )
                    
                    logger.info(f"Confirmação enviada no DM - Response: {response}")
                
            else:
                logger.warning("Nenhuma mensagem encontrada, não enviando confirmação")
                
        except Exception as e:
            logger.error(f"Erro ao enviar confirmação no DM: {e}")
            logger.error(f"Traceback: ", exc_info=True)
    
    def get_today_messages(self):
        """Buscar mensagens do usuário para hoje"""
        today = datetime.now().date().isoformat()
        logger.info(f"=== BUSCANDO MENSAGENS DO DIA ===")
        logger.info(f"Data de busca: {today}")
        
        try:
            conn = sqlite3.connect('messages.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT message FROM daily_messages WHERE date = ? ORDER BY timestamp",
                (today,)
            )
            
            messages = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"✅ {len(messages)} mensagens encontradas para {today}")
            for i, msg in enumerate(messages, 1):
                logger.info(f"  {i}. {msg}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens: {e}")
            logger.error(f"Traceback: ", exc_info=True)
            return []
    
    def create_daily_response(self, messages):
        """Criar resposta para a daily baseada nas mensagens do dia"""
        if not messages:
            return ""
        
        # Apenas as mensagens formatadas, sem título e sem total
        response = ""
        
        for i, message in enumerate(messages, 1):
            response += f"• {message}\n"
        
        # Remove a última quebra de linha
        response = response.rstrip('\n')
                
        return response
    
    def mark_daily_as_responded(self, date):
        """Marcar daily como respondida no banco"""
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO daily_responses (date, response_sent) VALUES (?, TRUE)",
            (date,)
        )
        
        conn.commit()
        conn.close()
    
    def reset_daily_flag(self):
        """Resetar flag de daily respondida (executado à meia-noite)"""
        self.daily_responded_today = False
        logger.info("Flag de daily resetada para novo dia")
    
    def check_missed_daily(self):
        """Verificar se perdeu alguma daily (executado às 23:55)"""
        today = datetime.now().date().isoformat()
        
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT response_sent FROM daily_responses WHERE date = ?",
            (today,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            # Ainda não respondeu - enviar lembrete
            messages = self.get_today_messages()
            if messages:
                response = f"⚠️ **Lembrete:** Daily ainda não foi respondida hoje!\n\n"
                response += self.create_daily_response(messages)
                
                if self.channel_id:
                    self.client.chat_postMessage(
                        channel=self.channel_id,
                        text=response
                    )
                
                logger.info("Lembrete de daily perdida enviado")
    
    def schedule_tasks(self):
        """Agendar tarefas automáticas"""
        # Resetar flag à meia-noite
        schedule.every().day.at("00:00").do(self.reset_daily_flag)
        
        # Verificar daily perdida às 23:55
        schedule.every().day.at("23:55").do(self.check_missed_daily)
        
        logger.info("Tarefas agendadas configuradas")
    
    def run_scheduler(self):
        """Executar agendador em thread separada"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
    
    def start_flask_with_ngrok(self):
        """Iniciar Flask e depois configurar ngrok"""
        def start_flask():
            logger.info(f"Servidor Flask iniciando na porta {self.port}")
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        
        # Iniciar Flask em thread separada
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        
        # Aguardar um pouco para o Flask inicializar
        time.sleep(2)
        
        # Agora configurar ngrok
        if self.use_ngrok:
            ngrok_url = self.setup_ngrok()
            if ngrok_url:
                logger.info("=" * 60)
                logger.info("CONFIGURAÇÃO DO SLACK APP:")
                logger.info(f"Event Subscriptions URL: {ngrok_url}/events")
                logger.info(f"Status do Bot: {ngrok_url}/status")
                logger.info(f"Health Check: {ngrok_url}/health")
                logger.info("=" * 60)
            else:
                logger.warning("Falha ao configurar ngrok, rodando apenas localmente")
        
        # Manter o programa rodando
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
    
    def start(self):
        """Iniciar o bot"""
        try:
            logger.info(f"Iniciando bot em modo: {'Webhook' if self.webhook_mode else 'Socket'}")
            
            # Configurar agendamentos
            self.schedule_tasks()
            
            # Iniciar scheduler em thread separada
            scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            scheduler_thread.start()
            
            if self.webhook_mode:
                # Modo Webhook com Flask
                logger.info("Iniciando em modo Webhook...")
                self.start_flask_with_ngrok()
                
            else:
                # Modo Socket (original)
                logger.info("Iniciando em modo Socket...")
                
                # Conectar ao Slack
                self.socket_client.connect()
                
                logger.info("Bot conectado com sucesso!")
                logger.info("Pressione Ctrl+C para parar o bot")
                
                # Manter o bot rodando
                while True:
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro ao iniciar bot: {e}")
        finally:
            # Cleanup
            if hasattr(self, 'socket_client'):
                self.socket_client.disconnect()
            if self.use_ngrok and self.ngrok_url:
                try:
                    ngrok.disconnect(self.ngrok_url)
                    ngrok.kill()
                except:
                    pass

def main():
    """Função principal"""
    try:
        # Carregar variáveis de ambiente do arquivo .env se existir
        if os.path.exists('.env'):
            from dotenv import load_dotenv
            load_dotenv()
        
        bot = DailyBot()
        bot.start()
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 

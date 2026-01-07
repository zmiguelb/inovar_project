import smtplib
import ssl
from email.message import EmailMessage
import sys
import configparser
import os
from typing import List

# --- CONFIGURAÇÃO ESTÁTICA ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587 # Porta padrão para TLS
CONFIG_FILE = "config.ini" # Nome do arquivo de configuração
# Nome do script de e-mail (ATENÇÃO: corrigido para corresponder ao nome do arquivo)
EMAIL_SCRIPT = "send_mail.py"

def send_gmail_email(sender_email: str, sender_password: str, receiver_list: List[str], subject: str, body: str):
    """
    Conecta-se ao servidor SMTP do Gmail usando TLS e envia um e-mail.

    Args:
        sender_email (str): O endereço de e-mail do remetente (sua conta Gmail).
        sender_password (str): A Senha de App gerada para a conta Gmail.
        receiver_list (List[str]): Lista de endereços de e-mail dos destinatários.
        subject (str): O assunto do e-mail.
        body (str): O corpo do e-mail (texto simples).
    """
    # Junta todos os destinatários em uma única string separada por vírgula para o cabeçalho 'To:'
    receiver_header = ", ".join(receiver_list)
    print(f"Tentando enviar e-mail para: {receiver_header}...")

    # Cria o objeto de e-mail
    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = receiver_header
    message["Subject"] = subject
    
    # Adiciona o corpo do e-mail. Substitui '\\n' por quebras de linha reais.
    message.set_content(body.replace(r'\n', '\n'))

    # Cria um contexto de segurança TLS
    context = ssl.create_default_context()

    try:
        # 1. Conecta-se ao servidor SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            # 2. Inicia o TLS (criptografia)
            server.starttls(context=context)
            
            # 3. Faz login usando o e-mail e a Senha de App
            server.login(sender_email, sender_password)
            
            # 4. Envia o e-mail. O método sendmail exige a lista de e-mails, não a string formatada.
            server.sendmail(sender_email, receiver_list, message.as_string())
            
        print("Sucesso: E-mail enviado com sucesso!")
        
    except smtplib.SMTPAuthenticationError:
        print("\nErro de Autenticação: Verifique se o seu e-mail e Senha de App estão corretos no arquivo config.ini.", file=sys.stderr)
        print("Lembre-se: Você DEVE usar uma Senha de App do Gmail, não sua senha regular.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nOcorreu um erro ao enviar o e-mail: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # O script agora espera o Assunto e o Corpo como argumentos de linha de comando.
    if len(sys.argv) < 3:
        print(f"Uso: python3 {sys.argv[0]} \"<Assunto do E-mail>\" \"<Corpo do E-mail>\"", file=sys.stderr)
        sys.exit(1)
        
    email_subject = sys.argv[1]
    email_body = sys.argv[2]

    # --- Carregamento e Validação da Configuração ---
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        print(f"ERRO: Arquivo de configuração '{CONFIG_FILE}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    try:
        config.read(CONFIG_FILE)
        
        # Leitura das credenciais
        sender_email = config.get('GMAIL', 'sender_email')
        app_password = config.get('GMAIL', 'app_password')
        
        # Leitura de múltiplos destinatários (separados por vírgula)
        receiver_emails_str = config.get('GMAIL', 'receiver_email')
        
        # Converte a string de e-mails em uma lista, limpando espaços
        receiver_list = [e.strip() for e in receiver_emails_str.split(',') if e.strip()]
        
    except configparser.Error as e:
        print(f"ERRO ao ler o arquivo de configuração {CONFIG_FILE}. Verifique a formatação.", file=sys.stderr)
        print(f"Detalhes: {e}", file=sys.stderr)
        sys.exit(1)

    # Verifica se os placeholders foram alterados
    if sender_email == "seu_email_aqui@gmail.com" or app_password == "sua_senha_de_app_aqui":
        print("ERRO: Por favor, edite o arquivo config.ini e substitua os placeholders pelas suas credenciais reais.", file=sys.stderr)
        sys.exit(1)
        
    if not receiver_list:
        print("ERRO: Nenhum destinatário válido encontrado em 'receiver_email' no config.ini.", file=sys.stderr)
        sys.exit(1)

    # Executa a função de envio com os dados lidos
    send_gmail_email(sender_email, app_password, receiver_list, email_subject, email_body)

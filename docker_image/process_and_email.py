import json
import sys
import re
from datetime import datetime
from subprocess import run, PIPE
import os

# --- CONFIGURAÇÃO DE ARQUIVOS E HEADERS ---
# O arquivo JSON que contém a agenda. Assumimos que foi ordenado anteriormente.
AGENDA_JSON_FILE = "agenda_sorted.json"
# O nome do script de envio de e-mail.
# CORREÇÃO: Alterado de "send_email.py" para "send_mail.py" para corresponder ao nome do arquivo.
EMAIL_SCRIPT = "send_mail.py"
# Headers que precisamos para processar
DATE_TIME_HEADER = "Data/Hora"
EVENTO_HEADER = "Evento"

def parse_datetime_from_data_hora(data_hora_str):
    """
    Parses 'DD-MM-YYYY (HH:MM-HH:MM)' into a datetime object, using the start time (HH:MM).
    This function is crucial for sorting and comparison.
    """
    # Regex para capturar DD-MM-YYYY e HH:MM (horário de início)
    match = re.match(r"(\d{2}-\d{2}-\d{4}) \((\d{2}:\d{2})-\d{2}:\d{2}\)", data_hora_str)
    if match:
        date_part, time_part = match.groups()
        datetime_str = f"{date_part} {time_part}"
        try:
            # Retorna o objeto datetime
            return datetime.strptime(datetime_str, "%d-%m-%Y %H:%M")
        except ValueError:
            return None
    return None

def format_event_for_email(event):
    """Formata um único evento em uma string legível para o corpo do e-mail."""
    data_hora = event.get(DATE_TIME_HEADER, "N/A")
    evento = event.get(EVENTO_HEADER, "N/A")
    professor = event.get("Professor", "N/A")
    
    # Formato: Data/Hora - Evento - Professor
    return f"- {data_hora}: {evento} (Prof. {professor})"

def main():
    # Obtém o diretório do script atual (process_and_email.py) para construir caminhos absolutos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Constrói o caminho completo para o script de e-mail (usado apenas para verificação de existência)
    email_script_path = os.path.join(script_dir, EMAIL_SCRIPT)
    
    try:
        # 1. Carregar Dados JSON
        json_file_path = os.path.join(script_dir, AGENDA_JSON_FILE)
        with open(json_file_path, 'r', encoding='utf-8') as f:
            agenda_data = json.load(f)
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados não encontrado: '{AGENDA_JSON_FILE}'.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERRO: O arquivo '{AGENDA_JSON_FILE}' não é um JSON válido.", file=sys.stderr)
        sys.exit(1)

    # Obter o momento atual (ignora milissegundos)
    now = datetime.now().replace(microsecond=0)
    closest_future_event = None
    future_events = []

    # 2. Filtragem e Busca do Evento Mais Próximo
    for event in agenda_data:
        data_hora_str = event.get(DATE_TIME_HEADER)
        if not data_hora_str:
            continue

        event_dt = parse_datetime_from_data_hora(data_hora_str)
        
        if event_dt and event_dt >= now:
            # Evento é igual ou posterior ao momento atual
            future_events.append(event)
            
            # Encontrar o evento futuro mais próximo
            if closest_future_event is None or event_dt < parse_datetime_from_data_hora(closest_future_event.get(DATE_TIME_HEADER)):
                closest_future_event = event

    # 3. Preparar Conteúdo
    if not future_events:
        subject = "Agenda: Nenhum evento futuro."
        body = "Não há testes ou eventos futuros agendados na agenda a partir de agora."
        print("INFO: Não há eventos futuros agendados. Não será enviado e-mail (ou enviado apenas o 'sem eventos').")
        sys.exit(0) # <-- ESSA É A LINHA QUE FALTAVA
    else:
        # A. Criar Assunto (Argumento 1)
        closest_dt_str = closest_future_event.get(DATE_TIME_HEADER, "N/A")
        closest_evento_str = closest_future_event.get(EVENTO_HEADER, "N/A")
        
        # Garante que o assunto está formatado exatamente como pedido
        subject = f"Próxima Avaliação: {closest_dt_str}-{closest_evento_str}"

        # B. Criar Corpo (Argumento 2 - Lista human-readable)
        formatted_list = [format_event_for_email(e) for e in future_events]
        
        # Constrói o corpo da mensagem com quebras de linha reais (\n)
        body_intro = f"Prezado(a),\n\nO próximo evento é: {subject.replace('Próxima Avaliação: ', '')}.\n\nTodos os {len(future_events)} eventos futuros agendados são:\n\n"
        body_list = "\n".join(formatted_list)
        body_outro = "\n\nEsta lista exclui todos os eventos que já ocorreram."
        
        body = body_intro + body_list + body_outro
 
    # -----------------------------------------------------------
    # 4. LÓGICA CONDICIONAL DE NOTIFICAÇÃO (NOVA SEÇÃO)
    # -----------------------------------------------------------

    # Extrair a data/hora do evento futuro mais próximo para comparação
    closest_event_dt = parse_datetime_from_data_hora(closest_future_event.get(DATE_TIME_HEADER))

    if not closest_event_dt:
        print("ERRO: Não foi possível obter ou analisar a data/hora do evento futuro mais próximo.", file=sys.stderr)
        sys.exit(1)
    # 1. Obter datas de comparação (ignorar a hora para a maioria das checagens)
    closest_event_date = closest_event_dt.date()
    now_date = now.date()
    # --- DEBUGGING PRINTS AQUI ---
    print(f"DEBUG: Data Atual (now_date): {now_date}")
    print(f"DEBUG: Data do Próximo Evento (closest_event_date): {closest_event_date}")
    # -----------------------------
    
    # Calcular a diferença em dias (apenas a parte de data)
    date_difference = closest_event_date - now_date
    
    # 1. Condição: Sábado e Próximo Evento em até 7 dias
    # weekday() retorna 5 para Sábado (Segunda=0, Domingo=6)
    is_saturday = (now.weekday() == 5)
    
    # Check se está entre 0 (hoje) e 7 dias de distância (máximo de 6 dias, 23 horas...)
    # O evento não pode ser no passado (date_difference.days >= 0)
    is_within_7_days = (0 <= date_difference.days <= 6)
    
    # A condição de Sábado é estritamente para eventos DENTRO da próxima semana.
    send_on_saturday_if_close = is_saturday and is_within_7_days and (date_difference.days > 0)

    # 2. Condição: É o dia do evento (hoje)
    # A diferença em dias é exatamente 0.
    is_day_of_event = (date_difference.days == 0)
    

    should_send_email = send_on_saturday_if_close or is_day_of_event

    if not should_send_email:
        # Não atendeu a nenhuma das condições de envio, então saímos.
        print(f"INFO: Condições de envio não atendidas hoje ({now.strftime('%A')} - Dia {now.day}).")
        if is_saturday:
             print(f"INFO: Sábado, mas o evento não está nos próximos 7 dias (diferença: {date_difference.days} dias).")
        if not is_day_of_event:
             print("INFO: Não é o dia do evento.")
        
        print("\n--- JSON Completo da Agenda (para Debug) ---")
        print(json.dumps(agenda_data, indent=2, ensure_ascii=False))
        print("-------------------------------------------\n")
        # ----------------------------------
        print("INFO: E-mail não será enviado.")
        sys.exit(0) # Saída bem-sucedida, sem necessidade de notificação

    # Se chegarmos aqui, should_send_email é True, então preparamos para enviar.
    print(f"INFO: Condições de envio atendidas (Sábado e <7 dias: {send_on_saturday_if_close}, Dia do Evento: {is_day_of_event}).")
    # -----------------------------------------------------------
    # FIM DA LÓGICA CONDICIONAL
    # -----------------------------------------------------------
 
    
    # 4. Chamar o send_email.py via Subprocess
    print("\n--- Chamando o script de E-mail ---")
    print(f"Assunto: {subject}")
    
    # Verifica se o script de e-mail existe
    if not os.path.exists(email_script_path):
        # Usamos EMAIL_SCRIPT aqui para mostrar o nome configurado na constante
        print(f"ERRO: O script de e-mail '{EMAIL_SCRIPT}' não foi encontrado no caminho: {email_script_path}", file=sys.stderr)
        print("VERIFIQUE: O nome do arquivo deve ser exatamente 'send_mail.py'.", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Lista de comandos: [interpretador, script_nome_simples, arg1 (subject), arg2 (body)]
        command = [
            sys.executable,
            EMAIL_SCRIPT, # Usamos o nome de arquivo CORRIGIDO
            subject,
            body
        ]
        
        # Executa o comando e captura a saída. check=True levanta exceção se o script falhar.
        result = run(
            command, 
            capture_output=True, 
            text=True, 
            check=True, 
            encoding='utf-8',
            cwd=script_dir # Define o diretório de trabalho do subprocesso
        )
        
        print(f"Subprocesso {EMAIL_SCRIPT} concluído com sucesso.")
        print("Saída do Subprocesso:")
        print(result.stdout)

    except Exception as e:
        # Captura erros de execução do subprocesso
        if hasattr(e, 'stderr') and e.stderr:
            print(f"ERRO na execução do subprocesso de e-mail:\n{e.stderr}", file=sys.stderr)
        else:
            print(f"ERRO ao executar o script de e-mail: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

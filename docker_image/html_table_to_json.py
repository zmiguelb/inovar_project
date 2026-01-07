import sys
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime # Importado para a lógica de ordenação

# Required dependencies: pip install beautifulsoup4 lxml.
# This script now includes a fallback to 'html.parser' if 'lxml' is not installed.

def get_sortable_datetime(event):
    """
    Função chave para a ordenação.
    Extrai a data (DD-MM-YYYY) e a hora de início (HH:MM) da string 'Data/Hora'
    e retorna um objeto datetime para ordenação cronológica.
    """
    if "Data/Hora" not in event or not event["Data/Hora"]:
        # Retorna a data mínima se a chave estiver faltando, colocando-a no início/fim.
        return datetime.min

    date_time_str = event["Data/Hora"]

    # Expressão regular para capturar a data (DD-MM-YYYY) e a hora de início (HH:MM)
    # Exemplo: "14-01-2026 (10:00-10:50)" -> ['14-01-2026', '10:00']
    match = re.search(r"(\d{2}-\d{2}-\d{4}).*\((\d{2}:\d{2})", date_time_str)

    if match:
        date_part = match.group(1)
        time_part = match.group(2)

        # Cria uma string combinada: "DD-MM-YYYY HH:MM"
        combined_dt_str = f"{date_part} {time_part}"

        try:
            # Converte para um objeto datetime para comparação
            return datetime.strptime(combined_dt_str, "%d-%m-%Y %H:%M")
        except ValueError:
             # Retorna data mínima se o formato for inválido
            print(f"Aviso: Formato de data/hora inválido em: {date_time_str}", file=sys.stderr)
            return datetime.min

    # Retorna uma data mínima para eventos que falhem na extração
    print(f"Aviso: Não foi possível extrair data e hora de: {date_time_str}", file=sys.stderr)
    return datetime.min

def report_error(message, required_headers=None, found_headers=None):
    """Prints a structured JSON error and exits."""
    error_dict = {"error": message}
    if required_headers:
        error_dict["required_headers"] = required_headers
    if found_headers:
        error_dict["found_headers"] = found_headers
    # Use ensure_ascii=False to correctly handle Portuguese characters
    print(json.dumps(error_dict, indent=4, ensure_ascii=False))
    sys.exit(1)

def normalize_text(text):
    """Normalizes text by lowercasing, stripping whitespace, and compacting internal spaces."""
    if text is None:
        return ""
    # Replace multiple internal whitespace characters (including newlines) with a single space, then strip.
    text = re.sub(r'\s+', ' ', text).lower().strip()
    return text

def convert_table_to_json():
    # Check for correct number of arguments
    if len(sys.argv) < 3:
        report_error(f"Usage: python3 {sys.argv[0]} <html_file> <header1> <header2> [header3]...",
                     required_headers=["<html_file>", "<header1>", "..."])

    html_filepath = sys.argv[1]
    required_headers = sys.argv[2:]

    # 1. Load HTML content
    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        report_error(f"Error: HTML file not found at path: {html_filepath}")
    except Exception as e:
        report_error(f"Error reading file: {e}")

    # 2. Parse HTML and find ALL tables

    # Try using 'lxml' first, fall back to 'html.parser' if lxml is missing (the cause of your error).
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except Exception:
        # Fallback to the built-in standard library parser
        print("Warning: 'lxml' parser not found. Falling back to 'html.parser'. To avoid this, run: pip install lxml", file=sys.stderr)
        soup = BeautifulSoup(html_content, 'html.parser')

    tables = soup.find_all('table')

    if not tables:
        report_error("Error: No <table> element found in the HTML file.", required_headers=required_headers)

    # Data structure to hold the first successful match
    best_match_data = None

    # Iterate through all tables to find the one containing the required headers
    for table in tables:

        # 3. Aggressively search for a header row within the current table
        header_rows_to_check = []

        # Check for headers in <thead> first
        thead = table.find('thead')
        if thead:
            header_rows_to_check.extend(thead.find_all('tr'))

        # Also check all <tr> elements directly under <tbody> or the table root,
        # in case <thead> isn't used or is incomplete.
        header_rows_to_check.extend(table.find_all('tr'))

        # Use a list to track rows already added from <thead> to avoid duplication
        unique_rows = []
        for row in header_rows_to_check:
            # Check for object identity to ensure we only process each row once
            if row not in unique_rows:
                unique_rows.append(row)

        for tr in unique_rows:
            # Extract clean text from <th> or <td> elements in the current row
            current_found_headers_list = [th.get_text(strip=True) for th in tr.find_all(['th', 'td'])]

            # Create a map of normalized HTML header text -> (original index)
            normalized_html_headers_map = {}
            for idx, header_text in enumerate(current_found_headers_list):
                normalized_key = normalize_text(header_text)
                if normalized_key:
                    normalized_html_headers_map[normalized_key] = idx

            # This map will store: {required_header_name (from CLI): column_index_in_html}
            temp_column_index_map = {}
            all_headers_present = True

            # Check if ALL required headers are present in this row
            for required_header in required_headers:
                normalized_required_key = normalize_text(required_header)
                if normalized_required_key in normalized_html_headers_map:
                    col_index = normalized_html_headers_map[normalized_required_key]
                    temp_column_index_map[required_header] = col_index
                else:
                    all_headers_present = False
                    break

            if all_headers_present:
                # Found a successful match! Store data and break table/row search.
                best_match_data = {
                    'table': table,
                    'header_row': tr,
                    'column_index_map': temp_column_index_map
                }
                break

        if best_match_data:
            break # Stop iterating over other tables

    if not best_match_data:
        report_error(
            f"Error: None of the tables found contained all the required headers ({', '.join(required_headers)}) after normalization. Please check the header names in your HTML.",
            required_headers=required_headers
        )

    # Proceed with extraction using the matched data
    table = best_match_data['table']
    header_row = best_match_data['header_row']
    column_index_map = best_match_data['column_index_map']

    # 5. Extract Data Rows
    json_data = []

    # Get the index and header list from the success map
    required_headers_for_json = list(column_index_map.keys())
    col_indices = [column_index_map[h] for h in required_headers_for_json]

    # Find all rows in the table
    data_rows = table.find_all('tr')

    # Remove the identified header row from the data rows list
    # Use a direct comparison of the BeautifulSoup tag objects
    try:
        if header_row in data_rows:
              data_rows.remove(header_row)
    except ValueError:
        # Header row might not be in the direct list if it was inside a <thead>
        pass

    for row in data_rows:
        cols = row.find_all(['td', 'th'])
        # Skip empty rows or rows that are clearly not data rows
        if not cols or len(cols) == 0:
            continue

        item = {}
        # Map the extracted cell data to the required header names
        for i, header in zip(col_indices, required_headers_for_json):
            if i < len(cols):
                item[header] = cols[i].get_text(strip=True)
            else:
                # Handle cases where a data row is 'ragged' (has fewer columns than expected)
                item[header] = None

        if item:
            json_data.append(item)

    # 6. Apply Sorting by Date/Hora
    # Check if the 'Data/Hora' key was requested and data exists before attempting to sort
    if "Data/Hora" in required_headers_for_json and json_data:
        try:
            # A ordenação será feita em ordem crescente (do mais antigo para o mais recente)
            json_data.sort(key=get_sortable_datetime)
            print("Info: Dados ordenados por 'Data/Hora' (mais antigo primeiro).", file=sys.stderr)
        except Exception as e:
            print(f"Aviso: Falha ao ordenar os dados por data. Erro: {e}", file=sys.stderr)
            # Continua sem ordenar se ocorrer um erro.

    # 7. Output JSON
    print(json.dumps(json_data, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    convert_table_to_json()


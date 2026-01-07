import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from pathlib import Path
import sys
import configparser
import os

# Define o nome do arquivo de configuração
CONFIG_FILE = "config.ini"

def load_config():
    """Carrega as configurações do arquivo config.ini."""
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        print(f"ERRO: Arquivo de configuração '{CONFIG_FILE}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    try:
        config.read(CONFIG_FILE)
        
        # Leitura da seção SELENIUM
        selenium_config = {
            "SELENIUM_HUB_URL": config.get('SELENIUM', 'selenium_hub_url'),
            "BASE_URL": config.get('SELENIUM', 'base_url'),
            "USERNAME": config.get('SELENIUM', 'username'),
            "PASSWORD": config.get('SELENIUM', 'password')
        }
        
        # Validação básica
        if any(not v for v in selenium_config.values()):
            print("ERRO: Certifique-se de que todas as variáveis (hub_url, base_url, username, password) estão definidas na seção [SELENIUM] do config.ini.", file=sys.stderr)
            sys.exit(1)
            
        return selenium_config
        
    except configparser.Error as e:
        print(f"ERRO ao ler o arquivo de configuração {CONFIG_FILE}. Verifique a seção [SELENIUM] e a formatação.", file=sys.stderr)
        print(f"Detalhes: {e}", file=sys.stderr)
        sys.exit(1)

# Carrega as configurações globalmente ao iniciar o script
CONFIG = load_config()

class InovarTest(unittest.TestCase):
    """
    Executes the Inovar navigation steps on a Selenium Grid 
    and saves the final page source to a file.
    Configuration is loaded from config.ini.
    """

    def setUp(self):
        # Usa a URL do Hub carregada do CONFIG
        selenium_hub_url = CONFIG["SELENIUM_HUB_URL"]
        print(f"Attempting to connect to Selenium Hub at: {selenium_hub_url}")
        
        # Define browser options for Chrome
        chrome_options = ChromeOptions()
        # chrome_options.add_argument("--headless") # Descomente para rodar sem interface gráfica

        # Initialize the WebDriver via the Remote connection to the Selenium Hub
        try:
            self.driver = webdriver.Remote(
                command_executor=selenium_hub_url,
                options=chrome_options
            )
        except Exception as e:
            print(f"Error connecting to Selenium Hub. Ensure the Grid is running at {selenium_hub_url}")
            # Lança o erro para falhar o setUp
            raise e
            
        self.driver.implicitly_wait(10) # Set a generous implicit wait
        self.base_url = CONFIG["BASE_URL"]
        self.driver.set_window_size(1070, 693)

    def test_inovar_save_page(self):
        driver = self.driver
        
        # Carrega credenciais do CONFIG
        username = CONFIG["USERNAME"]
        password = CONFIG["PASSWORD"]
        
        # 1. Open the initial page
        print("Navigating to login page...")
        driver.get(self.base_url + "/consulta/app/index.html")
        
        # Define locators for clarity
        USERNAME_FIELD = (By.CSS_SELECTOR, '[data-ng-model="userName"]')
        PASSWORD_FIELD = (By.CSS_SELECTOR, '[data-ng-model="userPassword"]')
        ATIVIDADES_LINK = (By.LINK_TEXT, "ATIVIDADES")
        AGENDA_LINK = (By.LINK_TEXT, "Agenda")

        try:
            # Wait for the username field to be present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(USERNAME_FIELD)
            )

            # 2. Input Username and Password using CONFIG values
            print("Entering credentials...")
            driver.find_element(*USERNAME_FIELD).click()
            driver.find_element(*USERNAME_FIELD).send_keys(username)
            driver.find_element(*PASSWORD_FIELD).send_keys(password)
            
            # 3. Log in by sending ENTER key
            driver.find_element(*PASSWORD_FIELD).send_keys(Keys.ENTER)
            
            # Wait for successful login and navigation menu to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(ATIVIDADES_LINK)
            )
            print("Login successful. Navigating to activities...")

            # 4. Click 'ATIVIDADES' to open the dropdown menu
            driver.find_element(*ATIVIDADES_LINK).click()
            
            # 5. Wait for the 'Agenda' link to become clickable
            print("Waiting for Agenda link in dropdown...")
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(AGENDA_LINK)
            )
            driver.find_element(*AGENDA_LINK).click()
            
            # 6. Wait for the 'Agenda' page content to load 
            wait_time=59
            print(f"Waiting some time ({wait_time}) to allow everything on page to load ...")
            time.sleep(wait_time) # Usamos um wait estático por robustez na automação

            print("Successfully reached the Agenda page.")
            
            # 7. Wait for the 'Agenda' Events to load
            WebDriverWait(driver, wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(., 'Eventos (Testes, trabalhos, atividades,...)')]"))
            )
            
            # === FINAL STEP: CAPTURE AND SAVE THE PAGE SOURCE ===
            
            page_content = driver.page_source
            output_file = Path("inovar_agenda.html")
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(page_content)
                
            print(f"\nSuccessfully saved the page content to: {output_file.resolve()}")

        except Exception as e:
            print(f"An error occurred during test execution: {e}")
            driver.save_screenshot("error_screenshot.png")
            self.fail(f"Test failed: {e}")

    def tearDown(self):
        # Close the browser
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == "__main__":
    # O unittest.main precisa de um argv ajustado quando chamado de forma programática.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

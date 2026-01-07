# inovar_project
Verifica se existem "novidades" no portal do Inovar 

```bash

# Caso seja necessário recriar o container inovar_project
# Correr isto dentro da pasta inovar_project/docker_image
# docker build -t inovar_project:v1 .


# 1. Launch Selenium
docker run -d --name selenium -p 4444:4444 -p 7900:7900 --shm-size="2g" selenium/standalone-chrome:140.0.7339.207-chromedriver-140.0.7339.207-grid-4.35.0-20250909

# 2. Wait for Selenium Grid to be Ready (The key step! 🔑)
echo "Waiting for Selenium Grid to be ready..."
until curl -s http://localhost:4444/status | grep '"ready": true' > /dev/null; do
    echo -n "."
    sleep 1
done
echo -e "\nSelenium Grid is ready! Starting project container."

# 3. Launch Inovar_Project 
docker run --rm --name inovar_project -v "./config.ini:/usr/src/app/config.ini" inovar_project:v1

# 4. Stop and remove Selenium
docker stop selenium && docker rm selenium
```

config.ini [Exemplo]
```bash
[SELENIUM]
#URL Selenium Grid Hub || Pode ser localhost se correm o container do selenium e da aplica��o python no mesmo docker
selenium_hub_url = http://localhost:4444/wd/hub

#URL base da aplicação Inovar (para driver.get())
#Cada escola deve ter o seu portal!!
base_url = https://agrupamentoeliasgarcia.inovarmais.com

#Credenciais de acesso
#Username do aluno
username = 123456
#Password do aluno - normalmente numero do Cartao do Cidadao!
password = abc123

[GMAIL]
#O endereço de e-mail (usado como login)
sender_email = bill_gates@gmail.com

#A senha de 16 caracteres gerada pelo Google (App Password)
#Ver https://myaccount.google.com/apppasswords para gerar a password
app_password = abcd efgh ijkl mnop

#O endereço de e-mail do destinatário
receiver_email = melissa_gates@gmail.com, steve_jobs@apple.com
```

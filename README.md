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
docker run --rm --name inovar_project -v "/root/container/selenium/config.ini:/usr/src/app/config.ini" inovar_project:v1

# 4. Stop and remove Selenium
docker stop selenium && docker rm selenium
```

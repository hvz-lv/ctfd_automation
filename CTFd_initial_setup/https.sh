#!/bin/bash

# Variables
REPO_URL="https://github.com/CTFd/CTFd.git"
DIR_NAME="CTFd"


# Clone the CTFd repository if it doesn't already exist
if [ ! -d "$DIR_NAME" ]; then
    echo "Cloning CTFd repository..."
    git clone "$REPO_URL"
else
    echo "Repository already exists. Pulling latest changes..."
    cd "$DIR_NAME" && git pull
fi

# Navigate to the CTFd directory
cd "$DIR_NAME" || { echo "Failed to navigate to directory $DIR_NAME"; exit 1; }

# Copy certificates to the appropriate directory
echo "Copying certificates..."
cp ../dhparams.pem ../fullchain.pem ../privkey.pem ./conf/nginx/

# Update docker-compose.yml
echo "Updating docker-compose.yml..."
cat <<EOL > docker-compose.yml
version: '3'

services:
  ctfd:
    build: .
    user: root
    restart: always
    privileged: true
    environment:
      - UPLOAD_FOLDER=/var/uploads
      - DATABASE_URL=mysql+pymysql://ctfd:ctfd@db/ctfd
      - REDIS_URL=redis://cache:6379
      - WORKERS=5
      - LOG_FOLDER=/var/log/CTFd
      - ACCESS_LOG=- 
      - ERROR_LOG=- 
      - REVERSE_PROXY=true
      - SECRET_KEY=thisisasecretkey
    volumes:
      - .data/CTFd/logs:/var/log/CTFd
      - .data/CTFd/uploads:/var/uploads
      - .:/opt/CTFd
    depends_on:
      - db
    networks:
      - default
      - internal

  nginx:
    image: nginx:1.17
    restart: always
    privileged: true
    volumes:
      - ./conf/nginx/http.conf:/etc/nginx/nginx.conf
      - ./conf/nginx/privkey.pem:/etc/nginx/nginx-selfsigned.key
      - ./conf/nginx/fullchain.pem:/etc/nginx/nginx-selfsigned.crt
      - ./conf/nginx/dhparams.pem:/etc/nginx/dhparams.pem
    ports:
      - 80:80
      - 443:443
    depends_on:
      - ctfd
    networks:
      - default
      - internal

  db:
    image: mariadb:10.11
    restart: always
    privileged: true
    environment:
      - MYSQL_ROOT_PASSWORD=ctfd
      - MYSQL_USER=ctfd
      - MYSQL_PASSWORD=ctfd
      - MYSQL_DATABASE=ctfd
      - MARIADB_AUTO_UPGRADE=1
    volumes:
      - .data/mysql:/var/lib/mysql
    networks:
      - internal
    command: [mysqld, --character-set-server=utf8mb4, --collation-server=utf8mb4_unicode_ci, --wait_timeout=28800, --log-warnings=0]

  cache:
    image: redis:4
    restart: always
    privileged: true
    volumes:
      - .data/redis:/data
    networks:
      - internal

networks:
  default:
  internal:
    internal: true
EOL

# Update Nginx configuration
echo "Updating Nginx configuration..."
cat <<EOL > conf/nginx/http.conf
worker_processes 4;

events {
  worker_connections 1024;
}

http {
  upstream app_servers {
    server ctfd:8000;
  }

  server {
    listen 80;
    listen 443 ssl;
    ssl_certificate /etc/nginx/nginx-selfsigned.crt;
    ssl_certificate_key /etc/nginx/nginx-selfsigned.key;
    ssl_dhparam /etc/nginx/dhparams.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:20m;
    ssl_session_timeout 180m;

    client_max_body_size 4G;
    gzip on;

    if (\$scheme != "https") {
        return 301 https://\$host\$request_uri;
    }

    location /events {
      proxy_pass http://app_servers;
      proxy_set_header Connection '';
      chunked_transfer_encoding off;
      proxy_buffering off;
      proxy_cache off;
      proxy_redirect off;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Host \$server_name;
    }

    location / {
      proxy_pass http://app_servers;
      proxy_redirect off;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Host \$server_name;
    }
  }
}
EOL

# Build and pull Docker containers
echo "Building Docker images..."
sudo docker compose build
echo "Pulling Docker images..."
sudo docker compose pull

# Start Docker containers
echo "Starting Docker containers..."
sudo docker compose up -d

# Wait for the initial setup to complete
echo "CTFd is starting. Please wait..."
sleep 10
echo "Checking for Python dependencies..."
python3 -m pip show requests >/dev/null 2>&1 || python3 -m pip install requests >/dev/null 2>&1
python3 -m pip show beautifulsoup4 >/dev/null 2>&1 || python3 -m pip install beautifulsoup4 >/dev/null 2>&1
cd ..
# Run the Python script to handle the CTFd setup
echo "Running CTFd setup..."
python3 ctfd_setup.py

echo "Setup complete."

# Define the container name
CONTAINER_NAME="ctfd-ctfd-1"  # Replace with actual container name

# Copy the Python script into the container
sudo docker cp /home/ubuntu/test/get_api.py $CONTAINER_NAME:/opt/CTFd/CTFd/utils/security/

# Run the Python script inside the container and capture the API key
API_KEY=$(sudo docker exec -it $CONTAINER_NAME python3 /opt/CTFd/CTFd/utils/security/get_api.py | grep "Generated Token:" | awk '{print $3}')

# Check if the API key was generated successfully
if [ -n "$API_KEY" ]; then
    echo "API Key generated successfully: $API_KEY"
    
    # Export the API key as an environment variable for Python scripts
    export API_KEY
    echo "API Key exported as environment variable."

    # Stop Docker containers for plugin installation
    echo "Stopping Docker containers..."
    sudo docker compose down

    # Install the first_blood plugin
    echo "Installing first_blood plugin..."
    cd CTFd/CTFd/plugins/
    git clone https://github.com/krzys-h/CTFd_first_blood.git

    # Rebuild and pull Docker containers with the plugin
    echo "Rebuilding Docker images with the plugin..."
    cd ../../
    sudo docker compose build
    sudo docker compose pull

    # Start Docker containers again
    echo "Starting Docker containers with the plugin..."
    sudo docker compose up -d
    sleep 15s

    # Run additional Python scripts using the API token
    echo "Running additional Python scripts..."
    python3 /home/ubuntu/test/ctfd_automatization/challenges.py $API_KEY
    python3 /home/ubuntu/test/ctfd_automatization/add_user.py $API_KEY
    docker builder prune -a -f

else
    echo "Failed to generate API Key."
fi

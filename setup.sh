#!/bin/bash

# Variables
homedir=$(pwd)
DIR_NAME="$homedir/CTFd"
AUTOMATION_DIR="$homedir/ctfd_automation"
PLUGIN_REPO="https://github.com/krzys-h/CTFd_first_blood.git"
CONTAINER_NAME="ctfd-ctfd-1"  # Replace with actual container name

# Function to start Docker containers
start_docker() {
    cd $DIR_NAME
    echo "Starting Docker containers..."
    sudo docker compose up -d
    echo "Docker containers started."
    sleep 5  # Wait for the containers to start properly
}

# Function to copy necessary files
copy_files() {
    echo "Copying necessary files..."

    # Ensure the destination directory exists
    mkdir -p $DIR_NAME/conf/nginx/

    # Copy necessary configuration files to CTFd directory
    cp -r $AUTOMATION_DIR/http.conf $DIR_NAME/conf/nginx/
    cp -r $AUTOMATION_DIR/dhparams.pem $DIR_NAME/conf/nginx/
    cp -r $AUTOMATION_DIR/privkey.pem $DIR_NAME/conf/nginx/
    cp -r $AUTOMATION_DIR/fullchain.pem $DIR_NAME/conf/nginx/
    cp -r $AUTOMATION_DIR/docker-compose.yml $DIR_NAME

#    cd $DIR_NAME/conf/nginx/
#    openssl req -newkey rsa:4096 -nodes -subj "/C=PT/ST=PT/O=IPB/CN=CTFD.IPB.PT" -keyout ./privkey.pem -x509 -days 3650 -out ./fullchain.pem
#    openssl dhparam -out ./dhparams.pem 4096
    
}

# Function to prompt for admin credentials
prompt_for_credentials() {
    echo "Please enter the admin credentials for the CTFd setup."

    read -p "Admin Username: " admin_username
    read -p "Admin Email: " admin_email

    # Read password with silent mode
    read -s -p "Admin Password: " admin_password
    echo  # Just to add a newline after password input

    # Confirm password
    read -s -p "Confirm Password: " admin_password_confirm
    echo  # Just to add a newline after password input

    while [[ "$admin_password" != "$admin_password_confirm" ]]; do
        echo "Passwords do not match. Please try again."
        read -s -p "Admin Password: " admin_password
        echo  # Newline after input
        read -s -p "Confirm Password: " admin_password_confirm
        echo  # Newline after input
    done
}

# Function to run Python setup scripts
run_python_scripts() {
    echo "Running Python setup scripts..."

    # Ensure the automation directory exists
    if [ -d "$AUTOMATION_DIR/CTFd_initial_setup" ]; then

        # Prompt for user mode
        read -p "Do you want to set up CTFd in user mode or team mode? (users/teams): " mode_choice
        
        while [[ "$mode_choice" != "users" && "$mode_choice" != "teams" ]]; do
            echo "Invalid choice. Please enter 'user' or 'team'."
            read -p "Do you want to set up CTFd in user mode or team mode? (users/teams): " mode_choice
        done

        # Prompt for admin credentials
        prompt_for_credentials

        # Run CTFd setup with the chosen mode and credentials first
        echo "Running CTFd Setup with mode: $mode_choice"
        python3 "$AUTOMATION_DIR/CTFd_initial_setup/ctfd_setup.py" "$mode_choice" "$admin_username" "$admin_email" "$admin_password"

        # Copy get_api.py into the container after ctfd_setup.py runs
        echo "Copying get_api.py into the Docker container..."
        sudo docker cp "$AUTOMATION_DIR/CTFd_initial_setup/get_api.py" "$CONTAINER_NAME:/opt/CTFd/CTFd/utils/security/"
        sleep 2  # Wait for the copy to complete

        # Run the script inside the container to get the API key
        echo "Retrieving API Key from the Docker container..."
        token=$(sudo docker exec -it "$CONTAINER_NAME" python3 /opt/CTFd/CTFd/utils/security/get_api.py | grep "Generated Token:" | awk '{print $3}')
        export token

        if [ -n "$token" ]; then
            echo "API Key generated successfully: $token"
            sleep 1  # Wait before running additional scripts

            if [[ $token =~ $'\r' ]]; then
                echo "The variable contains a carriage return."
                # Remove \r from the variable
                token=$(echo "$token" | tr -d '\r')
            fi    
        else
            echo "Failed to generate API Key."
        fi
    else
        echo "Automation directory not found."
    fi
}

# Function to install the first_blood plugin
install_first_blood_plugin() {
    echo "Preparing to install the first_blood plugin..."

    read -p "Do you want to install the first_blood plugin? (y/n): " install_plugin_choice

    if [[ "$install_plugin_choice" == "y" || "$install_plugin_choice" == "Y" ]]; then
        echo "Stopping Docker containers..."
        sudo docker compose down
        sleep 3  # Wait for the containers to stop

        echo "Installing first_blood plugin..."
        cd $DIR_NAME/CTFd/plugins/
        git clone "$PLUGIN_REPO"
        echo "first_blood plugin installed."
        cd $DIR_NAME
        sleep 2  # Wait after installation
        rebuild_docker
    else
        echo "Skipping first_blood plugin installation."
    fi
}

# Function to rebuild Docker containers and prune
rebuild_docker() {
    cd $DIR_NAME
    echo "Rebuilding Docker images..."
    sudo docker compose build
    sudo docker compose pull
    echo "Docker images rebuilt."
    sleep 5  # Wait for build completion

    # Start the Docker containers again
    start_docker

    # Prune unused Docker builder objects
    echo "Pruning unused Docker builder objects..."
    sudo docker builder prune -a -f
    echo "Docker builder objects pruned."
}

install_challenges() {
    if [ -n "$token" ]; then
        # Run additional scripts using the generated token
        read -p "Do you want to run Challenges Setup? (y/n): " run_choice

        if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
            python3 $AUTOMATION_DIR/CTFd_initial_setup/challenges.py $token
        else
            echo "Skipping Challenges Setup."
        fi

        if [[ "$mode_choice" == "users" ]]; then
            read -p "Do you want to run User Setup? (y/n): " run_choice

            if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
                python3 $AUTOMATION_DIR/CTFd_initial_setup/add_user.py $token
            else
                echo "Skipping User Setup."
            fi
        elif [[ "$mode_choice" == "teams" ]]; then
            read -p "Do you want to run Team and User Setup? (y/n): " run_choice

            if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
                python3 $AUTOMATION_DIR/CTFd_initial_setup/add_team_and_user.py $token
            else
                echo "Skipping Team and User Setup."
            fi
        fi

    fi
}

# Function to run the WireGuard script with user input
run_wireguard_script() {
    echo "Preparing to run WireGuard script..."

    wireguard_script_path="$AUTOMATION_DIR/wireguard_peers_add/wireguard.py"
    
    if [ -f "$wireguard_script_path" ]; then
        read -p "Do you want to run WireGuard Peer Setup? (y/n): " run_choice

        if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
            python3 $wireguard_script_path
            send_emails
        else
            echo "Skipping WireGuard Peer Setup."
        fi
    else
        echo "WireGuard script not found."
    fi
}

# Function to send emails
send_emails() {
    read -p "Do you want to send emails after creating CTFd and WireGuard peers? (y/n): " send_emails_choice

    if [[ "$send_emails_choice" == "y" || "$send_emails_choice" == "Y" ]]; then
        echo "Sending emails..."
        mailmerge --no-dry-run --no-limit
    else
        echo "Skipping email sending."
    fi
}

# Main execution
git clone https://github.com/CTFd/CTFd.git
copy_files
start_docker
run_python_scripts
install_first_blood_plugin
install_challenges
run_wireguard_script

echo "Script execution completed."

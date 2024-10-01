
#!/bin/bash

# Variables
homedir=$(pwd)
DIR_NAME="/home/ubuntu/CTFd"
AUTOMATION_DIR="/home/ubuntu/ctfd_automation"
PLUGIN_REPO="https://github.com/krzys-h/CTFd_first_blood.git"
CONTAINER_NAME="ctfd-ctfd-1"  # Replace with actual container name

if [ "$#" -eq 10 ]; then
  admin_username=$1
  admin_email=$2
  admin_password=$3
  mode_choice=$4
  install_plugin_choice=$5
  run_challenges_setup=$6
  run_user_setup=$7
  run_wireguard_setup=$8
  confirm_password=$9
  send_emails_choice=${10}
fi

# Check if the password matches
if [ "$admin_password" != "$confirm_password" ]; then
    echo "Error: Passwords do not match!"
    exit 1
fi


# Function to start Docker containers
start_docker() {
    cd $DIR_NAME
    echo "Starting Docker containers..."
    docker compose up -d
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

        if [ -z "$mode_choice" ]; then
          read -p "Do you want to set up CTFd in user mode or team mode? (users/teams): " mode_choice

          while [[ "$mode_choice" != "users" && "$mode_choice" != "teams" ]]; do
              echo "Invalid choice. Please enter 'user' or 'team'."
              read -p "Do you want to set up CTFd in user mode or team mode? (users/teams): " mode_choice
          done
        fi

        # Prompt for admin credentials
        if [ -z "$admin_username" ]; then
           prompt_for_credentials
        fi
        # Run CTFd setup with the chosen mode and credentials first
        echo "Running CTFd Setup with mode: $mode_choice"
        python3 "$AUTOMATION_DIR/CTFd_initial_setup/ctfd_setup.py" "$mode_choice" "$admin_username" "$admin_email" "$admin_password"

        # Copy get_api.py into the container after ctfd_setup.py runs
        echo "Copying get_api.py into the Docker container..."
        docker cp "$AUTOMATION_DIR/CTFd_initial_setup/get_api.py" "$CONTAINER_NAME:/opt/CTFd/CTFd/utils/security/"
        sleep 2  # Wait for the copy to complete

        # Run the script inside the container to get the API key
        echo "Retrieving API Key from the Docker container..."
        token=$(docker exec -it "$CONTAINER_NAME" python3 /opt/CTFd/CTFd/utils/security/get_api.py | grep "Generated Token:" | awk '{print $3}')
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
    if [ -z "$install_plugin_choice" ]; then
      read -p "Do you want to install the first_blood plugin? (y/n): " install_plugin_choice
    fi
    if [[ "$install_plugin_choice" == "y" || "$install_plugin_choice" == "Y" ]]; then
        echo "Stopping Docker containers..."
        docker compose down
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
    docker compose build
    docker compose pull
    echo "Docker images rebuilt."
    sleep 5  # Wait for build completion

    # Start the Docker containers again
    start_docker

    # Prune unused Docker builder objects
    echo "Pruning unused Docker builder objects..."
    docker builder prune -a -f
    echo "Docker builder objects pruned."
}
install_challenges() {
    if [ -n "$token" ]; then
        # Run additional scripts using the generated token
        if [ -z "$run_challenges_setup" ]; then
            read -p "Do you want to run Challenges Setup? (y/n): " run_choice
        else
            run_choice=$run_challenges_setup
        fi

        if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
            python3 "$AUTOMATION_DIR/CTFd_initial_setup/challenges.py" "$token"
        else
            echo "Skipping Challenges Setup."
        fi

        # Handle user or team setup based on the mode_choice
        if [[ "$mode_choice" == "users" ]]; then
            if [ -n "$run_user_setup" ]; then
                run_choice=$run_user_setup
            else
                read -p "Do you want to run User Setup? (y/n): " run_choice
            fi

            if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
                python3 "$AUTOMATION_DIR/CTFd_initial_setup/add_user.py" "$token"
            else
                echo "Skipping User Setup."
            fi

        elif [[ "$mode_choice" == "teams" ]]; then
            if [ -n "$run_user_setup" ]; then
                run_choice=$run_user_setup
            else
                read -p "Do you want to run Team and User Setup? (y/n): " run_choice
            fi

            if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
                python3 "$AUTOMATION_DIR/CTFd_initial_setup/add_team_and_user.py" "$token"
            else
                echo "Skipping Team and User Setup."
            fi
        fi
    else
        echo "Token not found. Cannot proceed with challenge setup."
    fi
}

#Function to run the WireGuard script with user input
run_wireguard_script() {
    echo "Preparing to run WireGuard script..."

    wireguard_script_path="$AUTOMATION_DIR/wireguard_peers_add/wireguard.py"

    if [ -f "$wireguard_script_path" ]; then
      if [ -z "$run_wireguard_setup" ]; then
        read -p "Do you want to run WireGuard Peer Setup? (y/n): " run_choice

        if [[ "$run_choice" == "y" || "$run_choice" == "Y" ]]; then
          python3 $wireguard_script_path
          send_emails
        else
          echo "Skipping WireGuard Peer Setup."
        fi
      else
        if [[ "$run_wireguard_setup" == "y" || "$run_wireguard_setup" == "Y" ]]; then
          python3 $wireguard_script_path
          send_emails
        else
          echo "Skipping WireGuard Peer Setup."
        fi
      fi
    else
        echo "WireGuard script not found."
    fi
}

# Function to send emails
send_emails() {
  if [ -z "$sends_emails_choice" ]; then
    read -p "Do you want to send emails after creating CTFd and WireGuard peers? (y/n): " send_emails_choice
  fi
  if [[ "$send_emails_choice" == "y" || "$send_emails_choice" == "Y" ]]; then
    echo "Sending emails..."
    mailmerge --no-dry-run --no-limit
  else
    echo "Skipping email sending."
  fi
}

# Main execution
start_docker
run_python_scripts
install_first_blood_plugin
install_challenges
run_wireguard_script

echo "Script execution completed."

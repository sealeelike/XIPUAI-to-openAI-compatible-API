# configure.py - User credentials configuration utility
import os
from dotenv import load_dotenv, set_key
import getpass

def setup_credentials():
    """
    Guides the user to input and save their XJTLU credentials to a .env file.
    This script should be run once before the first use of auth.py.
    """
    print("--- XJTLU GenAI Adapter Configuration ---")
    
    env_file = ".env"
    
    # Check if the .env file exists, create if not
    if not os.path.exists(env_file):
        print(f"'.env' file not found. A new one will be created.")
        with open(env_file, 'w') as f:
            pass # Create an empty .env file
    
    load_dotenv(dotenv_path=env_file)
    
    print("\nPlease provide your XJTLU credentials.")
    print("These will be stored locally in the '.env' file for the automation script to use.")
    print("This information will not be sent anywhere else.")
    
    # Get username
    default_username = os.getenv("XJTLU_USERNAME")
    prompt_username = f"Enter your XJTLU username (e.g., San.Zhang24) [{default_username or 'New User'}]: "
    user_username = input(prompt_username)
    if not user_username and default_username:
        user_username = default_username
        print(f"Using existing username: {user_username}")

    # Get password
    user_password = getpass.getpass("Enter your password (input will be hidden): ")
    
    if user_username and user_password:
        try:
            set_key(env_file, "XJTLU_USERNAME", user_username)
            set_key(env_file, "XJTLU_PASSWORD", user_password)
            print("\n✅ Credentials successfully saved to '.env' file.")
            print("You can now run 'auth.py' to fetch the session tokens.")
        except Exception as e:
            print(f"\n❌ Error saving credentials: {e}")
    else:
        print("\n❌ Username or password cannot be empty. Configuration aborted.")

if __name__ == "__main__":
    setup_credentials()
# auth.py - Automated session token retrieval for XJTLU GenAI (Headless Version)
import time
import os
import sys
from seleniumwire import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv, set_key
from datetime import datetime

# Global dictionary to store captured credentials from network requests.
captured_credentials = {
    "jm_token": None,
    "sdp_session": None
}

def print_info(message, level="INFO"):
    """Print formatted log messages with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "PROGRESS": "⏳"
    }.get(level, "ℹ️")
    print(f"[{timestamp}] {prefix} {message}")

def print_progress(message):
    """Print progress message that overwrites the same line"""
    sys.stdout.write(f"\r[{datetime.now().strftime('%H:%M:%S')}] ⏳ {message}...")
    sys.stdout.flush()

def fetch_tokens():
    """
    Launches a headless browser, performs SSO login, and intercepts network requests
    using Chrome DevTools Protocol (CDP) to capture dynamic session tokens.
  
    This function relies on credentials stored in the .env file.
    """
    # Load credentials from .env file
    load_dotenv()
    username = os.getenv("XJTLU_USERNAME")
    password = os.getenv("XJTLU_PASSWORD")

    if not username or not password:
        print_info("Error: XJTLU_USERNAME or XJTLU_PASSWORD not found in .env file.", "ERROR")
        print_info("Please run 'python configure.py' first to set up your credentials.", "ERROR")
        return None

    print_info("Starting XJTLU GenAI Token Fetcher (Headless Mode)")
    print_info("Initializing automated browser session...")

    # Configure selenium-wire to intercept network traffic
    selenium_wire_options = {
        'disable_encoding': True,  # To view raw headers
        'suppress_connection_errors': False
    }
  
    chrome_options = webdriver.ChromeOptions()
    
    # Headless mode configuration
    chrome_options.add_argument("--headless=new")  # New headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Suppress logs
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = None
    try:
        print_progress("Creating headless Chrome instance")
        driver = webdriver.Chrome(
            seleniumwire_options=selenium_wire_options,
            options=chrome_options
        )
        print()  # New line after progress
        print_info("Headless Chrome browser initialized successfully")

        # Define a request interceptor to capture headers
        def interceptor(request):
            # Only check requests to the target domain
            if 'xipuai.xjtlu.edu.cn' in request.url:
                jm_token_val = request.headers.get('Jm-Token')
                sdp_session_val = request.headers.get('Sdp-App-Session')

                if jm_token_val and not captured_credentials["jm_token"]:
                    captured_credentials["jm_token"] = jm_token_val
                    print_info("Successfully intercepted 'Jm-Token' from network request", "SUCCESS")

                if sdp_session_val and not captured_credentials["sdp_session"]:
                    captured_credentials["sdp_session"] = sdp_session_val
                    print_info("Successfully intercepted 'Sdp-App-Session' from network request", "SUCCESS")

        driver.request_interceptor = interceptor
        print_info("Network interceptor deployed and monitoring requests")

        # --- Automation Flow ---
        print_info("=== Starting authentication flow ===")
        
        # Step 1: Navigate to login page
        print_progress("Step 1/3: Loading XJTLU GenAI login page")
        driver.get("https://xipuai.xjtlu.edu.cn/")
        print()
        print_info("Login page loaded successfully")
      
        # Wait for and fill login form
        print_progress("Waiting for login form to appear")
        username_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "username_show"))
        )
        print()
        print_info("Login form detected")
        
        print_info(f"Entering credentials for user: {username[:3]}***{username[-2:]}")
        username_field.send_keys(username)
        driver.find_element(By.ID, "password_show").send_keys(password)
        
        print_progress("Submitting login form")
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "#btn_login input"))
        print()
        print_info("Login form submitted")

        # Step 2: Navigate through post-login pages
        print_progress("Step 2/3: Waiting for post-login redirect")
        chat_link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/v3/chat']"))
        )
        print()
        print_info("Successfully logged in, navigating to chat interface")
        
        chat_link.click()

        print_progress("Waiting for chat interface to load")
        button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button:has(span.n-button__content)"))
        )
        print()
        print_info("Chat interface loaded, proceeding to final step")
        
        button.click()

        # Step 3: Wait for final page
        print_progress("Step 3/3: Initializing final page and capturing tokens")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
        )
        print()
        print_info("Final page loaded, monitoring network requests for tokens")
      
        # Allow time for initial API calls to be made and intercepted
        token_wait_time = 8
        start_time = time.time()
        
        while time.time() - start_time < token_wait_time:
            elapsed = int(time.time() - start_time)
            remaining = token_wait_time - elapsed
            
            if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
                print()
                print_info("All required tokens captured successfully!", "SUCCESS")
                break
            
            print_progress(f"Waiting for tokens... {remaining}s remaining")
            time.sleep(0.5)
        
        print()  # New line after progress

        # --- Verification ---
        if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
            print_info("=== Token Retrieval Summary ===")
            print_info(f"✓ Jm-Token: {'*' * 20}...{captured_credentials['jm_token'][-10:]}", "SUCCESS")
            print_info(f"✓ Sdp-App-Session: {'*' * 20}...{captured_credentials['sdp_session'][-10:]}", "SUCCESS")
            return captured_credentials
        else:
            print_info("Failed to capture one or more required tokens", "ERROR")
            if not captured_credentials["jm_token"]:
                print_info("Missing: 'Jm-Token' was not found in any request headers", "ERROR")
            if not captured_credentials["sdp_session"]:
                print_info("Missing: 'Sdp-App-Session' was not found in any request headers", "ERROR")
            
            # Save screenshot for debugging
            screenshot_path = "auth_error_headless.png"
            driver.save_screenshot(screenshot_path)
            print_info(f"Debug screenshot saved to '{screenshot_path}'")
            return None

    except TimeoutException as e:
        print()  # Clear progress line
        print_info(f"A timeout occurred during automation: {e}", "ERROR")
        if driver:
            screenshot_path = "auth_timeout_error_headless.png"
            driver.save_screenshot(screenshot_path)
            print_info(f"Debug screenshot saved to '{screenshot_path}'")
        return None
    except Exception as e:
        print()  # Clear progress line
        print_info(f"An unexpected error occurred: {e}", "ERROR")
        if driver:
            screenshot_path = "auth_unexpected_error_headless.png"
            driver.save_screenshot(screenshot_path)
            print_info(f"Debug screenshot saved to '{screenshot_path}'")
        return None
    finally:
        if driver:
            print_info("Cleaning up: Closing headless browser session")
            driver.quit()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   XJTLU GenAI Token Fetcher - Headless Edition")
    print("="*60 + "\n")
  
    retrieved_tokens = fetch_tokens()
  
    if retrieved_tokens:
        env_file = ".env"
        try:
            set_key(env_file, "JM_TOKEN", retrieved_tokens['jm_token'])
            set_key(env_file, "SDP_SESSION", retrieved_tokens['sdp_session'])
            print()
            print_info("Successfully updated JM_TOKEN and SDP_SESSION in '.env' file", "SUCCESS")
            print_info("You can now start the API adapter service", "SUCCESS")
            print("\n" + "="*60 + "\n")
        except Exception as e:
            print_info(f"Error writing tokens to .env file: {e}", "ERROR")
    else:
        print()
        print_info("Token retrieval failed. Please check the logs above for details", "ERROR")
        print("\n" + "="*60 + "\n")

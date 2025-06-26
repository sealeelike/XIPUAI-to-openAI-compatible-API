# auth.py - Automated session token retrieval for XJTLU GenAI
import time
import os
from seleniumwire import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv, set_key

# Global dictionary to store captured credentials from network requests.
captured_credentials = {
    "jm_token": None,
    "sdp_session": None
}

def fetch_tokens():
    """
    Launches a browser, performs SSO login, and intercepts network requests
    using Chrome DevTools Protocol (CDP) to capture dynamic session tokens.
    
    This function relies on credentials stored in the .env file.
    """
    # Load credentials from .env file
    load_dotenv()
    username = os.getenv("XJTLU_USERNAME")
    password = os.getenv("XJTLU_PASSWORD")

    if not username or not password:
        print("❌ Error: XJTLU_USERNAME or XJTLU_PASSWORD not found in .env file.")
        print("Please run 'python configure.py' first to set up your credentials.")
        return None

    print("Initializing automated browser session...")
    print("A Chrome window will open. Please wait patiently, no user input is required.")

    # Configure selenium-wire to intercept network traffic
    selenium_wire_options = {
        'disable_encoding': True  # To view raw headers
    }
    
    chrome_options = webdriver.ChromeOptions()
    # Uncomment the next line to run in headless mode for server environments
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = None
    try:
        driver = webdriver.Chrome(
            seleniumwire_options=selenium_wire_options,
            options=chrome_options
        )

        # Define a request interceptor to capture headers
        def interceptor(request):
            jm_token_val = request.headers.get('Jm-Token')
            sdp_session_val = request.headers.get('Sdp-App-Session')

            if jm_token_val and not captured_credentials["jm_token"]:
                captured_credentials["jm_token"] = jm_token_val
                print("  [INFO] Intercepted 'Jm-Token'.")

            if sdp_session_val and not captured_credentials["sdp_session"]:
                captured_credentials["sdp_session"] = sdp_session_val
                print("  [INFO] Intercepted 'Sdp-App-Session'.")

        driver.request_interceptor = interceptor
        print("Network interceptor deployed.")

        # --- Automation Flow ---
        print("Step 1/3: Navigating and performing SSO login...")
        driver.get("https://xipuai.xjtlu.edu.cn/")
        
        # Wait for and fill login form
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "username_show"))
        ).send_keys(username)
        
        driver.find_element(By.ID, "password_show").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "#btn_login input"))

        print("Step 2/3: Navigating through post-login pages...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/v3/chat']"))
        ).click()

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button:has(span.n-button__content)"))
        ).click()

        print("Step 3/3: Waiting for final page to initialize...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
        )
        print("Page initialized. Finalizing token capture...")
        
        # Allow time for initial API calls to be made and intercepted
        end_time = time.time() + 8
        while time.time() < end_time:
            if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
                print("All tokens captured ahead of schedule.")
                break
            time.sleep(0.5)

        # --- Verification ---
        if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
            print("\n✅ Token retrieval successful.")
            return captured_credentials
        else:
            print("\n❌ Failed to capture one or more tokens via network interception.")
            if not captured_credentials["jm_token"]:
                print("   - 'Jm-Token' was not found in any request headers.")
            if not captured_credentials["sdp_session"]:
                print("   - 'Sdp-App-Session' was not found in any request headers.")
            driver.save_screenshot("auth_error.png")
            print("   Screenshot saved to 'auth_error.png' for debugging.")
            return None

    except TimeoutException as e:
        print(f"\n❌ A timeout occurred during automation: {e}")
        if driver:
            driver.save_screenshot("auth_timeout_error.png")
            print("   Screenshot saved to 'auth_timeout_error.png'.")
        return None
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        if driver:
            driver.save_screenshot("auth_unexpected_error.png")
            print("   Screenshot saved to 'auth_unexpected_error.png'.")
        return None
    finally:
        if driver:
            print("Closing browser session.")
            driver.quit()

if __name__ == "__main__":
    print("--- XJTLU GenAI Token Fetcher ---")
    
    retrieved_tokens = fetch_tokens()
    
    if retrieved_tokens:
        env_file = ".env"
        try:
            set_key(env_file, "JM_TOKEN", retrieved_tokens['jm_token'])
            set_key(env_file, "SDP_SESSION", retrieved_tokens['sdp_session'])
            print("\n✅ Successfully updated JM_TOKEN and SDP_SESSION in '.env' file.")
            print("You can now start the API adapter service.")
        except Exception as e:
            print(f"\n❌ Error writing tokens to .env file: {e}")
    else:
        print("\nToken retrieval failed. Please check the logs for more details.")
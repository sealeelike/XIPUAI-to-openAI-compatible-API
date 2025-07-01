# auth.py - Automated session token retrieval for XJTLU GenAI (Headless Version)
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
    Launches a headless browser, performs SSO login, and intercepts network requests
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

    print("🚀 Initializing headless browser session...")
    print("📝 Running in headless mode - no browser window will appear")
    print(f"👤 Using username: {username[:3]}***{username[-3:] if len(username) > 6 else '***'}")

    # Configure selenium-wire to intercept network traffic
    selenium_wire_options = {
        'disable_encoding': True  # To view raw headers
    }
  
    chrome_options = webdriver.ChromeOptions()
    # Enable headless mode
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_options.add_argument("--proxy-server=direct://")  # 明确指定直连模式
    chrome_options.add_argument("--disable-proxy-discovery")  # 禁用自动代理检测

    driver = None
    try:
        print("🔧 Starting Chrome driver in headless mode...")
        driver = webdriver.Chrome(
            seleniumwire_options=selenium_wire_options,
            options=chrome_options
        )
        print("✅ Chrome driver initialized successfully")

        # Define a request interceptor to capture headers
        def interceptor(request):
            jm_token_val = request.headers.get('Jm-Token')
            sdp_session_val = request.headers.get('Sdp-App-Session')

            if jm_token_val and not captured_credentials["jm_token"]:
                captured_credentials["jm_token"] = jm_token_val
                print("🔑 [TOKEN] Successfully intercepted 'Jm-Token'")

            if sdp_session_val and not captured_credentials["sdp_session"]:
                captured_credentials["sdp_session"] = sdp_session_val
                print("🔑 [TOKEN] Successfully intercepted 'Sdp-App-Session'")

        driver.request_interceptor = interceptor
        print("🕸️  Network interceptor deployed and monitoring requests...")

        # --- Automation Flow ---
        print("\n📋 Starting SSO authentication process...")
        print("Step 1/3: 🌐 Navigating to XJTLU GenAI portal...")
        driver.get("https://xipuai.xjtlu.edu.cn/")
        print("✅ Successfully loaded login page")
      
        # Wait for and fill login form
        print("⏳ Waiting for login form to appear...")
        username_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "username_show"))
        )
        print("📝 Filling in username...")
        username_field.send_keys(username)
        
        print("📝 Filling in password...")
        driver.find_element(By.ID, "password_show").send_keys(password)
        
        print("🔘 Clicking login button...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "#btn_login input"))
        print("✅ Login form submitted")

        print("\nStep 2/3: 🔄 Processing post-login navigation...")
        print("⏳ Waiting for post-login page to load...")
        chat_link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/v3/chat']"))
        )
        print("🔗 Found chat link, clicking...")
        chat_link.click()
        print("✅ Successfully navigated to chat section")

        print("⏳ Waiting for chat interface to initialize...")
        chat_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button:has(span.n-button__content)"))
        )
        print("🔘 Found chat button, clicking...")
        chat_button.click()
        print("✅ Chat interface activated")

        print("\nStep 3/3: 🔍 Finalizing token capture...")
        print("⏳ Waiting for textarea element to confirm page is ready...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
        )
        print("✅ Chat interface fully loaded")
        print("🔍 Monitoring network traffic for authentication tokens...")
      
        # Allow time for initial API calls to be made and intercepted
        token_capture_duration = 8
        print(f"⏰ Waiting up to {token_capture_duration} seconds for token capture...")
        
        end_time = time.time() + token_capture_duration
        progress_counter = 0
        while time.time() < end_time:
            if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
                print("🎉 All required tokens captured successfully!")
                break
            
            # Show progress every 2 seconds
            if progress_counter % 4 == 0:
                remaining = int(end_time - time.time())
                tokens_status = []
                if captured_credentials["jm_token"]:
                    tokens_status.append("Jm-Token ✅")
                else:
                    tokens_status.append("Jm-Token ⏳")
                    
                if captured_credentials["sdp_session"]:
                    tokens_status.append("Sdp-Session ✅")
                else:
                    tokens_status.append("Sdp-Session ⏳")
                    
                print(f"📊 Status: {' | '.join(tokens_status)} | Time remaining: {remaining}s")
            
            progress_counter += 1
            time.sleep(0.5)

        # --- Verification ---
        print("\n🔍 Verifying token capture results...")
        if captured_credentials["jm_token"] and captured_credentials["sdp_session"]:
            print("✅ SUCCESS: All authentication tokens captured successfully!")
            print(f"🔑 Jm-Token: {captured_credentials['jm_token'][:20]}...{captured_credentials['jm_token'][-10:]}")
            print(f"🔑 Sdp-Session: {captured_credentials['sdp_session'][:20]}...{captured_credentials['sdp_session'][-10:]}")
            return captured_credentials
        else:
            print("❌ FAILURE: Unable to capture all required tokens")
            missing_tokens = []
            if not captured_credentials["jm_token"]:
                missing_tokens.append("'Jm-Token'")
            if not captured_credentials["sdp_session"]:
                missing_tokens.append("'Sdp-App-Session'")
            print(f"📝 Missing tokens: {', '.join(missing_tokens)}")
            
            print("📸 Saving screenshot for debugging...")
            driver.save_screenshot("auth_error.png")
            print("💾 Screenshot saved to 'auth_error.png'")
            return None

    except TimeoutException as e:
        print(f"\n⏰ TIMEOUT ERROR: {e}")
        print("📝 The automation process took longer than expected")
        if driver:
            print("📸 Saving timeout screenshot for debugging...")
            driver.save_screenshot("auth_timeout_error.png")
            print("💾 Screenshot saved to 'auth_timeout_error.png'")
        return None
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        print("📝 An unexpected error occurred during the automation process")
        if driver:
            print("📸 Saving error screenshot for debugging...")
            driver.save_screenshot("auth_unexpected_error.png")
            print("💾 Screenshot saved to 'auth_unexpected_error.png'")
        return None
    finally:
        if driver:
            print("🔚 Closing headless browser session...")
            driver.quit()
            print("✅ Browser session closed successfully")

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 XJTLU GenAI Token Fetcher (Headless Mode)")
    print("=" * 50)
  
    retrieved_tokens = fetch_tokens()
  
    if retrieved_tokens:
        env_file = ".env"
        try:
            print("\n💾 Saving tokens to .env file...")
            set_key(env_file, "JM_TOKEN", retrieved_tokens['jm_token'])
            set_key(env_file, "SDP_SESSION", retrieved_tokens['sdp_session'])
            print("✅ SUCCESS: Tokens saved to '.env' file successfully!")
            print("🚀 You can now start the API adapter service.")
        except Exception as e:
            print(f"❌ ERROR: Failed to save tokens to .env file: {e}")
    else:
        print("\n❌ FAILURE: Token retrieval unsuccessful")
        print("📋 Please check the logs above for detailed error information")
        print("💡 Tip: Check the generated screenshot files for visual debugging")
        
    print("=" * 50)

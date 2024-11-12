'''
Quick test made in 1 hour
NOT main
'''

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
from tqdm import tqdm
from dotenv import load_dotenv
import os
import numpy as np
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)
start_time = time.time()

headless_mode = False
path = r"C:\Users\Alexa\chromedriver-win64\chromedriver.exe"
website = 'https://atlas.emory.edu/'

'''
X-Path:
Semester: //*[@id="crit-srcdb"]
Subject: //*[@id="crit-subject"]
'''

'''
Postman or https://docs.mitmproxy.org/stable/mitmproxytutorial-interceptrequests/
Look up html proxy for selenium
'''
webdriver_service = Service(path)
chrome_options = Options()

chrome_options.add_argument("start-maximized")
chrome_options.add_argument("--auto-open-devtools-for-tabs")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)


capabilities = DesiredCapabilities.CHROME
capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

driver = webdriver.Chrome(service=webdriver_service, options=chrome_options, desired_capabilities=capabilities)
errors = []
wait = WebDriverWait(driver, timeout=20, poll_frequency=0.2, ignored_exceptions=errors)

all_responses = []

def extract_responses():
    logs = driver.get_log("performance")
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if "Network.responseReceived" in log["method"]:
            try:
                response = log['params']
                url = response.get("url")
                mime_type = response.get("mimeType")
                
                # Filter for JSON responses
                if "application/json" in mime_type:
                    request_id = log["params"]["requestId"]
                    response_body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    all_responses.append({"url": url, "body": json.loads(response_body["body"])})
                    logger.info((all_responses[-1]))
            except Exception as e:
                print(f"Failed to fetch response: {e}")
                logger.error(f"Failed to fetch response: {e}")

# Attach listener for responseReceived events
driver.execute_cdp_cmd('Network.enable', {})

driver.get(website)

driver.execute_script("console.log('Test site opened.')")

# X-Path buttons
sem_button = driver.find_element(by=By.XPATH, value = '//*[@id="crit-srcdb"]')
subject_button = driver.find_element(by=By.XPATH, value = '//*[@id="crit-subject"]')

semester_select = Select(sem_button)
subject_select = Select(subject_button)


def getNetwork():
    return driver.execute_script("""
        var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
        var network = performance.getEntries() || {};
        return network.filter(item => item.initiatorType === "xmlhttprequest" && item.responseStart > 0);
    """)

for semester_option in tqdm(semester_select.options):
    semester_select.select_by_visible_text(semester_option.text)
    
    for subject_option in subject_select.options[1:]:
        subject_select.select_by_visible_text(subject_option.text)
        
        # Trigger search or form submission if needed
        search_button = driver.find_element(By.XPATH, '//*[@id="search-button"]')  # Adjust XPATH as per actual button

        print(f"SEARCHING: {semester_option.text}, {subject_option.text}")
        search_button.click()
        
        # Wait for the results to load and network calls to complete
        time.sleep(1)  # Replace with a better wait condition if available

        extract_responses()


driver.quit()

with open('all_responses.json', 'w') as file:
    json.dump(all_responses, file, indent=4)

print(f"Finished run. Took {time.time() - start_time:.2f} seconds")

# input("INPUT")

# try:
#     network_data = getNetwork()
    
#     # Filter JSON responses
#     for entry in network_data:
#         if "api" in entry['name']:  # Adjust if you have specific URLs to capture
#             print(entry)
#             try:
#                 response_url = entry['name']
#                 driver.execute_script(f"fetch('{response_url}').then(r => r.json()).then(console.log)")
                
#                 response = driver.execute_script(f"""
#                     return fetch("{response_url}")
#                     .then(res => res.json())
#                     .catch(err => console.error(err));
#                 """)
#                 all_responses.append(response)
#             except Exception as e:
#                 print(f"Error fetching {entry['name']}: {e}")
# except Exception as e:
#     print(f"Error Networks {entry['name']}: {e}")

# # Save all collected JSON responses
# with open('all_responses.json', 'w') as file:
#     json.dump(all_responses, file, indent=4)

# driver.close()

'''
Run main: includes course-specific data rather than outer data data
'''

from seleniumwire import webdriver
from selenium.common import exceptions
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, ElementClickInterceptedException
import time
from tqdm import tqdm
from dotenv import load_dotenv
import os
import numpy as np
import pandas as pd
import json
import logging
import zlib # some gzip utility for string, non StringIO
import numpy as np
from collections import deque

load_dotenv()

logging.basicConfig(filename='main.log', encoding='utf-8', level=logging.ERROR)
logger = logging.getLogger(__name__)
start_time = time.time()

headless_mode = False # have not tested with headless
# chromedriver path
path = os.getenv("PATH")
website = 'https://atlas.emory.edu/'

'''
X-Path:
Semester: //*[@id="crit-srcdb"]
Subject: //*[@id="crit-subject"]

Course: /html/body/main/div[2]/div/div[3]/div/a
Back: //a[contains(@class, 'panel__back')]

Section: //a[contains(@class, 'course-section')]

Course Title: //div[contains(@class, "text col-8 detail-title margin--tiny text--huge")]

Career/School: //*[@id="crit-career"]
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

def extract_response():
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
driver.execute_script("document.body.style.zoom='25%'")

# X-Path buttons
sem_button = driver.find_element(by=By.XPATH, value = '//*[@id="crit-srcdb"]')
subject_button = driver.find_element(by=By.XPATH, value = '//*[@id="crit-subject"]')
career_button = driver.find_element(by =By.XPATH, value = '//*[@id="crit-career"]')
courses_xpath = '/html/body/main/div[2]/div/div[3]/div/a'
section_xpath = "//a[contains(@class, 'course-section')]"
course_title_xpath = '//div[contains(@class, "text col-8 detail-title margin--tiny text--huge")]'

semester_select = Select(sem_button)
subject_select = Select(subject_button)
career_select = Select(career_button)

career_select.select_by_visible_text("Emory College")

allowed_api_routes = set(['https://atlas.emory.edu/api/?page=fose&route=details'])

def getNetwork():
    return driver.execute_script("""
        var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
        var network = performance.getEntries() || {};
        return network.filter(item => item.initiatorType === "xmlhttprequest" && item.responseStart > 0);
    """)

def scrollElem(element):
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", element)
    # Wait for scroll to complete by checking the current position repeatedly
    previous_position = driver.execute_script("return window.pageYOffset;")
    
    while True:
        time.sleep(0.1)  # Wait briefly for scrolling
        current_position = driver.execute_script("return window.pageYOffset;")
        if current_position == previous_position:
            break  # Scrolling complete
        previous_position = current_position

def element_is_clickable(element):
    return element.is_displayed() and element.is_enabled()

def wait_until_all_sections_clicked(section_containers):
    """Ensure all sections have been processed before moving to the next course."""
    for section in section_containers:
        wait.until_not(EC.element_to_be_clickable(section))

# TMP VAR BEFORE JSON CONFIG
START_COURSE = 960

class Splitter:
    def __init__(self, start, end, batch_size = 30):
        vals = np.arange(start, end, batch_size)
        self.res = []

        for i in range(1, len(vals)):
            self.res.append((vals[i-1], vals[i]))
        
        if vals[i] != end:
            self.res.append((vals[i], end))
    
    def yield_split(self):
        for elem in self.res:
            yield (elem, f"--{START_COURSE}-{elem[1]}")


def write_json(lbl):
    with open(os.path.join('Data',f'ECAS_data{lbl}.json'), 'w') as file:
        json.dump(all_responses, file, indent=4)

for semester_option in semester_select.options:
    semester_select = Select(sem_button)

    if semester_option.text != "Fall 2023":
        continue

    semester_select.select_by_visible_text(semester_option.text)
    
    # Trigger search or form submission if needed
    search_button = driver.find_element(By.XPATH, '//*[@id="search-button"]')  # Adjust XPATH as per actual button

    print(f"SEARCHING: {semester_option.text}")
    search_button.click()
    
    # Wait for the results to load and network calls to complete
    time.sleep(1)  # Replace with a better wait condition if available

    # click through all courses to prompt network calls
    
    vis = set()
    course_containers = []
    try:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, courses_xpath)))
    except:
        logger.critical("::ERROR FINIDING COURSES::")
        continue

    course_containers = driver.find_elements(By.XPATH, courses_xpath)

    time.sleep(1)

    pbar = tqdm(total= len(course_containers))
    pbar.n = START_COURSE
    splitter = Splitter(START_COURSE, len(course_containers)-1, 30)
    
    splitter_gen = splitter.yield_split()
    try:
        (start,end), label = next(splitter_gen)
    except StopIteration:
        print("ITERATIONS COMPLETE. GENERATOR EMPTY")
        logger.error("ITERATIONS COMPLETE. GENERATOR EMPTY")

    for i in range(len(course_containers)):
        if i < start:
            continue
        if i >= end:
            print("LENGTH OF RESPONSES::",len(all_responses))
            # save batch
            write_json(label)
            all_responses = []
            (start,end), label = next(splitter_gen)
        try:
            wait.until(EC.presence_of_all_elements_located((By.XPATH, courses_xpath)))
            # find again since staleness issues here
            course_containers = driver.find_elements(By.XPATH, courses_xpath)
            course = course_containers[i]
            scrollElem(course)

            wait.until(EC.presence_of_all_elements_located((By.XPATH, courses_xpath)))
            # find again since staleness issues here
            course_containers = driver.find_elements(By.XPATH, courses_xpath)
            course = course_containers[i]

            wait.until(lambda d: element_is_clickable(course))

            try:
                driver.execute_script("arguments[0].click();", course)
                #course.click()
            except ElementClickInterceptedException as e:
                print(f"SECTION CLICK ERROR::Course Container NUM::{i}.")
                logger.error(f"SECTION CLICK ERROR::Course Container NUM::{i}.")
                logger.critical(f"FAILED TO HANDLE CLICK EXCEPTION:::{course.get_attribute('data-group')}.")

            time.sleep(1)
            course_title = driver.find_element(By.XPATH, course_title_xpath).text

            section_containers = []
            section_containers = driver.find_elements(By.XPATH, section_xpath)

            time.sleep(1)

            if len(section_containers) > 1 and "Special Topics" not in course_title:
                for j in range(len(section_containers)):
                    wait.until(EC.presence_of_all_elements_located((By.XPATH, section_xpath)))
                    # find again since staleness issues here
                    section_containers = driver.find_elements(By.XPATH, section_xpath)
                    section = section_containers[j]

                    if "course-section--not-matched" in section.get_attribute("class"):
                        # covered in course
                        print(f"Skipping: {course_title}")
                        continue
                    #scrollElem(section)

                    # time.sleep(1)

                    # # rerun to guarantee no stale
                    # wait.until(EC.presence_of_all_elements_located((By.XPATH, section_xpath)))
                    # section_containers = driver.find_elements(By.XPATH, section_xpath)
                    # section = section_containers[j]

                    try:
                        wait.until(lambda d: element_is_clickable(section))
                        section.click()
                        time.sleep(1)
                    except ElementClickInterceptedException as e:
                        print(f"SECTION CLICK ERROR::Course Container NUM::{course_title}::SECTION NUM: {j}")
                        logger.error(f"SECTION CLICK ERROR::Course Container NUM::{course_title}::SECTION NUM: {j}")
                        logger.critical(f"FAILED TO HANDLE CLICK EXCEPTION:::{course_title}.")

                # wait_until_all_sections_clicked(section_containers)
            
            for request in driver.requests:
                if request.response and 'application/json' in request.response.headers.get('Content-Type', ''):
                    if request.url not in allowed_api_routes:
                        continue
                    
                    # HANDLE CONTENT
                    response_body = zlib.decompress(request.response.body, 16 + zlib.MAX_WBITS).decode('utf-8')
                    # print(f"URL: {request.url}")
                    #print(f"Response: {response_body}")
                    
                    try:
                        json_response = json.loads(response_body)
                        hashed_json = json.dumps(json_response)
                        if json_response.get('key') != "Varies by section" and hashed_json not in vis:
                            # Save data
                            all_responses.append(json_response)
                            vis.add(hashed_json)
                    except json.decoder.JSONDecodeError as e:
                        print(f"JSON DECODER ERROR::Course Container NUM::{course_title}. RESPONSE: {response_body}")
                        logger.error(f"JSON DECODER ERROR::Course Container NUM::{course_title}. RESPONSE: {response_body}")
            
            # clear requests, need to consider better way to avoid duplicates
            driver.requests.clear()
                    

        except StaleElementReferenceException as e:
            print(f"2. STALE ELEMENT DETECTED::Course Container NUM::{i}.")
            logger.error(f"2. STALE ELEMENT DETECTED::Course Container NUM::{i}.")
        
        except TimeoutException as e:
            # tends to happen on empty/deprecated subjects
            # log for further review
            print(f"TIMEOUT_EXCEPTION DETECTED::Course Container NUM::{i}.")
            logger.error(f"TIMEOUT_EXCEPTION DETECTED::Course Container NUM::{i}.")
        
        pbar.update()
        
        #extract_response()
    
    time.sleep(1)
    back_button = driver.find_elements(by=By.XPATH, value = "//a[contains(@class, \'panel__back')]")[-1]
    back_button.click()
    time.sleep(1)
    sem_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="crit-srcdb"]')))
    subject_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="crit-subject"]')))



driver.quit()

pbar.close()
print(f"Finished run. Took {time.time() - start_time:.2f} seconds")
import time
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PropertyScrapper:
    def __init__(self, url, timeout=10):
        self.url = url
        self.data = []
        self.driver = self.initialize_driver()
        self.wait = WebDriverWait(self.driver, timeout=timeout)

    def initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument(
            "--enable-features=NetworkServiceInProcess")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver

    def wait_for_page_to_load(self):
        title = self.driver.title
        try:
            self.wait.until(
                lambda d: d.execute_script(
                    "return document.readyState") == "complete"
            )
        except:
            print(f"the webpage {title} did not fully loaded")
        else:
            print(f"The page {title} fully loaded")

    def access_website(self):
        self.driver.get(self.url)
        self.wait_for_page_to_load()

    def search_properties(self, text):
        # locating properties and entering into search bar
        try:
            search_bar = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="keyword2"]'))
            )
        except:
            print("timeout while locating search bar")
        else:
            search_bar.send_keys(text)
            time.sleep(2)

        # selecting valid option from list

        try:
            valid_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="0"]'))
            )
        except:
            print("Time out while locating valid option")
        else:
            valid_option.click()
            time.sleep(2)

        # click on search button

        try:
            search_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, "//button[@id='searchform_search_btn']")

                ))
        except:
            print("Time out while finding search button")
        else:
            search_button.click()
            self.wait_for_page_to_load()

    def adjust_budget_slider(self, offset):
        try:
            slider = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="budgetLeftFilter_max_node"]'))
            )
        except:
            print("Timeout while cheking the budget slider")

        else:
            actions = ActionChains(self.driver)
            (
                actions.click_and_hold(slider)
                .move_by_offset(offset, 0)
                .release()
                .perform()
            )
            time.sleep(2)

    def apply_filters(self):

        # varified

        varified = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='Verified']"))

        )
        varified.click()
        time.sleep(1)

        # ready to move

        ready_to_move = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='Ready To Move']"))

        )
        ready_to_move.click()
        time.sleep(1)

        # moving right side
        while True:
            try:
                right_button = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//i[contains(@class,'iconS_Common_24 icon_upArrow cc__rightArrow')]"))
                )
            except:
                print("Time out becuase we have covered all filters")
                break
            else:
                right_button.click()
                time.sleep(1)

        # with photos

        with_photos = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='With Photos']"))

        )
        with_photos.click()
        time.sleep(1)

        with_video = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[normalize-space()='With Videos']"))

        )
        with_video.click()
        time.sleep(10)

    def extract_data(self, row, by, value):
        try:
            return row.find_element(by, value).text
        except:
            return np.nan

    def scrape_webpage(self):
        rows = self.driver.find_elements(
            By.CLASS_NAME, "tupleNew__TupleContent")
        for row in rows:
            property = {
                "name": self.extract_data(row, By.CLASS_NAME, "tupleNew__headingNrera"),
                "location": self.extract_data(row, By.CLASS_NAME, "tupleNew__propType"),
                "price": self.extract_data(row, By.CLASS_NAME, "tupleNew__priceValWrap")
            }

            try:
                elements = row.find_elements(
                    By.CLASS_NAME, "tupleNew__area1Type")
            except:
                property["area"], property["bhk"] = [np.nan, np.nan]
            else:
                property["area"], property["bhk"] = [
                    ele.text for ele in elements]

            self.data.append(property)

    def navigate_pages_and_scrap(self):
        page_count = 0
        while True:
            page_count += 1
            try:
                self.scrape_webpage()
                next_page_btn = self.driver.find_element(
                    By.XPATH, "//a[normalize-space()='Next Page >']")
            except:
                print(f"we have scraped {page_count} pages")
                break
            else:
                try:
                    self.driver.execute_script(
                        "window.scrollBy(0, arguments[0].getBoundingClientRect().top - 100);", next_page_btn)
                    time.sleep(2)
                    self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Next Page >']"))).click()
                    time.sleep(5)
                except:
                    print("Timeout while clicking on \"Next Page\".\n")

    def clean_data_and_save_as_excel(self, file_name):
        df_properties = (
            pd
            .DataFrame(self.data)
            .drop_duplicates()
            .apply(lambda col: col.str.strip().str.lower() if col.dtype == "object" else col)
            .assign(
                is_starred=lambda df_: df_.name.str.contains("\n").astype(int),
                name=lambda df_: (
                    df_
                    .name
                    .str.replace("\n[0-9.]+", "", regex=True)
                    .str.strip()
                    .replace("adroit district s", "adroit district's")
                ),
                location=lambda df_: (
                    df_
                    .location
                    .str.replace("ahmedabad", "")
                    .str.strip()
                    .str.replace(",$", "", regex=True)
                    .str.split("in")
                    .str[-1]
                    .str.strip()
                ),
                price=lambda df_: (
                    df_
                    .price
                    .str.replace("₹", "")
                    .apply(lambda val: float(val.replace("lac", "").strip()) if "lac" in val else float(val.replace("cr", "").strip()) * 100)
                ),
                area=lambda df_: (
                    df_
                    .area
                    .str.replace("sqft", "")
                    .str.strip()
                    .str.replace(",", "")
                    .pipe(lambda ser: pd.to_numeric(ser))
                ),
                bhk=lambda df_: (
                    df_
                    .bhk
                    .str.replace("bhk", "")
                    .str.strip()
                    .pipe(lambda ser: pd.to_numeric(ser))
                )
            )
            .rename(columns={
                "price": "price_lakhs",
                "area": "area_sqft"
            })
            .reset_index(drop=True)
        )
        df_properties.to_excel(f"{file_name}.xlsx", index=False)

    def run(self, text="Ahmedabad", offset=-100, filename="properties"):
        try:
            self.access_website()
            self.search_properties(text)
            self.adjust_budget_slider(offset)
            self.apply_filters()
            self.navigate_pages_and_scrap()
            self.clean_data_and_save_as_excel(filename)
        finally:
            time.sleep(2)
            self.driver.quit()


if __name__ == "__main__":
    scrapper = PropertyScrapper(url="https://www.99acres.com/")
    scrapper.run(text="Ahmedabad",
                 offset=-73,
                 filename="Ahmedabad Properties"
                 )

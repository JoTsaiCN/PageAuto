# -*- coding: utf-8 -*-
from selenium import webdriver
from pageauto import get_page_with_yaml


if __name__ == '__main__':
    driver = webdriver.Chrome()
    driver.get("https://github.com")
    page = get_page_with_yaml('.\github_index.yaml', driver)

    page.header.search.input.send_keys('PageAuto')
    page.header.search.popup.click()
    print(driver.current_url)
    if driver.current_url == 'https://github.com/search?q=pageauto':
        print('Failed to jump to search result')
    else:
        print('Jump to search result')
    driver.quit()

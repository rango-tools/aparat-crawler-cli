__author__ = "Amirhossein Douzendeh Zenoozi"
__license__ = "MIT"
__version__ = "1.0"
__proxy__ = False
__doc__ = """
Aparat CLI Crawler
Usage:
    aparat.py archive [--browser] [--page=<page-number>] <url>
    aparat.py video [--browser] <videoID>
    aparat.py -h | --help
    aparat.py -v | --version

------------------------------------------------------------------

Options:
    --page=<page-number>        Total Pages.
    --browser                   Showing Browser if You Need.
    -h --help                   Show this screen.
    -v --version                Show version.
"""

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from docopt import docopt
from tqdm import tqdm

import os
import sqlite3
import json
import time

class AparatCrawler:
    def __init__(self, **kwargs):
        # DataBase Connection Config
        self.userAgent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
        self.showBrowser = kwargs.get('showBrowser', True)
        self.youtubeDlOptions = {}
        self.dataBaseConnection = sqlite3.connect(f'aparat.db')

        try:
            if (not os.path.exists('un_proccessed.txt')):
                f = open('un_proccessed.txt', 'w')
                f.close()
        except Exception as error:
            print(error)
            pass
        
        try:
            self.dataBaseConnection.execute('''CREATE TABLE aparat_videos
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id CHAR(50),
                categories_list TEXT NOT NULL,
                view_count INTEGER,
                video_title TEXT NOT NULL)''')
        except sqlite3.Error as error:
            print(error)
            pass

        # Selenium Driver Options
        self.driverOption = webdriver.ChromeOptions()
        self.driverOption.add_argument(f'user-agent={self.userAgent}')
        self.driverOption.add_argument('log-level=3')

        if( not self.showBrowser ):
            self.driverOption.add_argument('headless')

        self.driver = webdriver.Chrome(options=self.driverOption)
        self.driver.maximize_window()

    def process_archive_page( self, archiveUrl, toPage ):
        archiveUrl = f'{archiveUrl}'
        self.driver.get(archiveUrl)
        totalVideos = []
        videosWrapperElem = []


        for pageNumber in range(toPage or 1):
            # Get Single Archive Page Video ID's
            videosWrapperElem = [v.get_attribute('data-uid') for v in self.driver.find_elements(By.CSS_SELECTOR, 'div.thumbnail-video') if str(v.get_attribute('data-uid')) not in totalVideos]
            for videoID in videosWrapperElem:
                if (not self.is_video_processed(videoID) and not self.is_video_saved_in_unProccessed(videoID)):
                    self.insert_video_to_unProccessed(videoID)
                    self.infinite_scroll(5, 1)
            totalVideos = totalVideos + videosWrapperElem

    def process_un_processed_file(self):
        with open("un_proccessed.txt", "r") as fp:
            unProccessedVideos = fp.readlines()
        
        for line in tqdm(unProccessedVideos):
            videID = line.strip("\n")
            if self.process_single_video(videID):
                self.remove_video_from_unProccessed(videID)

    def process_single_video( self, videoID ):
        if (not self.is_video_processed(videoID)):
            generatedVideoUrl = f'https://www.aparat.com/v/{videoID}'
            self.driver.get(generatedVideoUrl)
            
            # Empty Lists
            videoTitle = ''
            viewCount = ''
            videoCategories = []

            try:
                FollowBtn = WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.button.follow.add-button')))

                videoTitle = self.driver.find_element(By.CSS_SELECTOR, 'h1.single-details__title').text
                viewCount = int(self.driver.find_element(By.CSS_SELECTOR, 'div.single-details__view > span.view-text').text.replace(',', ''))

                for cat in self.driver.find_elements(By.CSS_SELECTOR, 'div.item-tag.video-tag a'):
                    videoCategories.append(cat.text) 

                self.insert_video_details_to_database(videoID, json.dumps(videoCategories), viewCount, videoTitle)

                return True

            except exceptions.TimeoutException:
                print("=========== TimeOut Getting Element! ===========")
        else:
            print(f'=========== This Video is already proccessed! ===========')
        
        return False

    def is_video_processed( self, videoID ):
        database_record = self.dataBaseConnection.execute("""SELECT * FROM aparat_videos WHERE video_id = (?) LIMIT 1""", (videoID,)).fetchone()
        return database_record

    def is_video_saved_in_unProccessed(self, videoID):
        with open("un_proccessed.txt", "r") as fp:
            unProccessedVideos = fp.readlines()
            for line in unProccessedVideos:
                if line.strip("\n") == videoID:
                    return True
                else:
                    return False

    def insert_video_details_to_database( self, videoID, categoriesList, viewCount, videoTitle ):
        try:
            self.dataBaseConnection.execute("""INSERT INTO aparat_videos (video_id, categories_list, view_count, video_title) VALUES (?, ?, ?, ?)""", (videoID, categoriesList, viewCount, videoTitle))
            self.dataBaseConnection.commit()
        except sqlite3.Error as error:
            print(error)
            pass

    def insert_video_to_unProccessed(self, videoID):
        with open("un_proccessed.txt", "a+") as fp:
            # Move read cursor to the start of file.
            fp.seek(0)
            # If file is not empty then append '\n'
            data = fp.read(100)
            if len(data) > 0 :
                fp.write("\n")
            
            # Append text at the end of file
            fp.write(videoID)

    def remove_video_from_unProccessed(self, videoID):
        with open("un_proccessed.txt", "r") as input:
            input.seek(0)
            with open("temp_un_proccessed.txt", "w") as output:
                # iterate all lines from file
                for line in input:
                    # if text matches then don't write it
                    if line.strip("\n") != videoID:
                        output.write(line)
                    else:
                        print(line.strip("\n"), videoID)


        # replace file with original name
        os.replace('temp_un_proccessed.txt', 'un_proccessed.txt')

    def infinite_scroll(self, timeout, counte):
        scrollPauseTime = timeout

        # Get scroll height
        lastHeight = self.driver.execute_script("return document.body.scrollHeight")
        loopIndex = 0

        while ( loopIndex <= counte ):
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep( scrollPauseTime )
            # Calculate new scroll height and compare with last scroll height
            newHeight = self.driver.execute_script("return document.body.scrollHeight")
            if newHeight == lastHeight:
                # If heights are the same it will exit the function
                break
            lastHeight = newHeight
            
            # Make Infinite Loop
            if ( counte != 0 ):
                loopIndex += 1

    def close_driver( self ):
        self.dataBaseConnection.close()
        self.driver.close()
        self.driver.quit()

def main():
    arguments = docopt(__doc__, version='v1.0')
    pageNumber = int(arguments['--page'])
    showBrowser = arguments['--browser']
    pageUrl = arguments['<url>']
    videoID = arguments['<videoID>']

    aparat = AparatCrawler(showBrowser=showBrowser)

    if ( arguments['video'] ):
        aparat.process_single_video( videoID=videoID )
    elif ( arguments['archive'] ):
        aparat.process_archive_page( pageUrl, toPage=pageNumber )
        aparat.process_un_processed_file()
    
    aparat.close_driver()

if __name__ == '__main__':
    main()

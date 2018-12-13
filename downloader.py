from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
import argparse
import sys
import os
import re

home_url = 'https://echo360.org/home'

parser = argparse.ArgumentParser(description='Download Echo360 videos for UIUC.')
parser.add_argument('-e', 
	type=str, dest='email', required=True, help='UIUC school email')

parser.add_argument('-p', 
	type=str, dest='password', required=True, help='UIUC NetId Password')

parser.add_argument('-c', 
	type=str, dest='course_name', required=True, help='The Course You want to download. e.g "CS 425"')

def set_up_driver(email, netId, password):
	options = webdriver.ChromeOptions()
	options.add_argument('user-agent = Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')
	driver = webdriver.Chrome(chrome_options=options, executable_path=os.getcwd() + '/chromedriver')
	driver.get(home_url)
	
	
	#enter email
	driver.find_element_by_name("email").send_keys(email)
	driver.find_element_by_id("submitText").click()
	
	#enter Credential
	driver.find_element_by_id("j_username").send_keys(netId)
	driver.find_element_by_id("j_password").send_keys(password)
	driver.find_element_by_name("_eventId_proceed").click()
	
	driver.get(home_url + '?all=true')

	driver.implicitly_wait(4)

	return driver

#get all courses meta data
def get_course_meta_list(driver):
	content = driver.find_elements_by_partial_link_text('ALL CLASSES')
	meta_list = []
	for c in content:
		course_id = c.get_attribute('id')
		course_label = c.get_attribute('aria-label')
		course_href = c.get_attribute('href')
		meta_list.append((course_id, course_label, course_href))

	return meta_list


def set_session_cookie(s, cookies):
	for cookie in cookies:
		s.cookies.set(cookie['name'], cookie['value'])

	return s


def get_section_ids(driver, course_url):
	driver.get(course_url)
	content = driver.find_elements_by_class_name('questions-link')

	section_ids = []
	for c in content:
		question_url = c.get_attribute('href')
		section_id = re.split(r'/', question_url)[-2]
		section_ids.append(section_id)

	return section_ids


def get_video_urls(driver, section_id):
	driver.get('https://echo360.org/lesson/' + section_id + '/classroom#sortDirection=desc')
	content = driver.find_elements_by_tag_name('video')
	video_urls = []
	for c in content:
		video_urls.append(c.get_attribute('src'))

	return video_urls

def download_file(url, session, local_filename):
	# NOTE the stream=True parameter
	r = session.get(url, stream=True)
	with open(local_filename, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024): 
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)
				
	return local_filename

if __name__ == '__main__':
	args = parser.parse_args()
	email = args.email
	netId = email.split('@')[0]
	password = args.password
	course_name = args.course_name

	s = requests.session()

	video_content_list = []
	
	driver = set_up_driver(email, netId, password)
	meta_list = get_course_meta_list(driver)

	selected_courses = [c for c in meta_list if course_name in c[1]]

	for selected_course in selected_courses:
		section_ids = get_section_ids(driver, selected_course[2])
		dates = driver.find_elements_by_class_name('date')
		dates = [d.text for d in dates]

		for date, section_id in zip(dates, section_ids):
			video_url_list = get_video_urls(driver, section_id)
			video_content_list.append({"date": date, "video_urls": video_url_list})

	s = set_session_cookie(s, driver.get_cookies())

	try:
		os.mkdir(course_name)
	except OSError:
		print(course_name + 'Already exists')

	for video_content in video_content_list:
		path = course_name + '/' + video_content['date']
		try:
			os.makedirs(path)
		except OSError:
			print('directory already exists')

		i = 1
		for video_url in video_content['video_urls']:
			download_file(video_url, s, path + '/video' + str(i) + '.mp4')
			print(video_url + ': ' + str(i) + ' Downloaded')
			i += 1




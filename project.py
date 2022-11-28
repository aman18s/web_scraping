#!/usr/bin/env python
import requests
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from time import sleep, strftime
from datetime import datetime
from timeit import default_timer as timer
from datetime import datetime, timedelta
from argparse import ArgumentParser

# ########################################################################################
# #/Function/
# ########################################################################################
def get_args(valid_destinations):
    parser = ArgumentParser(valid_destinations)
    parser.add_argument('-s', '--start', type = str, choices = valid_destinations.index)
    parser.add_argument('-e', '--end', type = str, choices = valid_destinations.index)
    parser.add_argument('-d', '--duration', type = int, choices = range(1, 21))
    args = parser.parse_args()
    start_location = args.start
    end_location = args.end
    duration = args.duration
    start_code = valid_destinations.loc[start_location]['IATA Code']
    end_code = valid_destinations.loc[end_location]['IATA Code']
    return start_code, end_code, duration
def get_airports_data():
    # get a list of avaialble international airport names, codes and their city
    URL = "https://en.wikipedia.org/wiki/List_of_international_airports_by_country"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    tables = soup.find_all("table", class_ = 'wikitable')
    airports = [str(table) for table in tables]
    airport_df = [pd.read_html(airport)[0] for airport in airports]
    airport_df = pd.concat(airport_df)[['Location', 'Airport', 'IATA Code']]
    airport_df= airport_df.dropna().drop_duplicates(subset = 'IATA Code').set_index('Location')
    return airport_df
def get_driver():
    chromedriver_path = 'chromedriver_win32/chromedriver.exe'
    driver = webdriver.Chrome(executable_path=chromedriver_path) # This will open the Chrome window
    sleep(2)
    return driver
def visit_website(start_location, end_location, start_date, end_date, trip_duration, driver):
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    URL = f'https://www.kayak.com.hk/flights/{start_location}-{end_location}/{start_date}/{end_date}-flexible-calendar-{trip_duration}?sort=bestflight_a'
    driver.get(URL)
    sleep(15)

def get_flights_table(driver):
    # The website produces a table of around 4 to 6 weeks of data, with this function we can get the table list
    trips_list = driver.find_elements_by_xpath('//*[contains(@class,"calendarMonthContainer calendarVisible")]')
    return [trips.text.split('\n') for trips in trips_list]

def get_departure_info(flights_table, driver):
    # Get all the departure information and
    # The index of each price element is stored so in future we can click into it for more info regarding the return flight
    trips_info = []
    index = -1
    for trips in flights_table:
        index, tmp = extract_info_from_matrix(index, trips)
        trips_info += tmp
    trips_info = [{'departure_date' : value[0], 'departure_index' : value[2]} for value in trips_info]
    new_start_date = datetime.strptime(trips_info[-1]['departure_date'], '%d %b %Y') + timedelta(days = 2)
    return trips_info, new_start_date

def get_return_info(flights_table, driver):
    flight_links_name = []
    # Use the index from get_departure_info and click into it to get all avaialble departure dates and the prices
    for i in range(len(flights_table)):
        count = -1
        index = flights_table[i]['departure_index']
        position = driver.find_elements_by_xpath(
            '//*[contains(@class,"calendarMonthContainer calendarVisible")]/div/div/div/div[2]'
            )[index]
        position.click()
        sleep(3)
        return_flights = get_flights_table(driver)[-1]
        links = driver.find_elements_by_xpath('//*[contains(@id,"booking-link")]')
        flight_links_name += [link.get_attribute('href') for link in links]
        count, trips = extract_info_from_matrix(count, return_flights)
        flights_table[i]['return_options'] = [{
            'return_date' : value[0],
            'price' : value[1],
        } for value in trips]
        # Close the sub-element when information is extracted so we can move on to the next element
        driver.find_elements_by_xpath('//*[contains(@class,"Button-No-Standard-Style close")]')[-1].click()
        sleep(2)
    return flights_table, flight_links_name

def extract_info_from_matrix(count, trips, direction = 'departure'):
    # The matrix has rows of infomation in which it stores dates, prices and more, this function to extracts these info
    tmp = []
    day = trips[8]
    month = trips[0]
    infos = trips[8:]    #infos contain price in HK$ and date information
    for info in infos:
        if info[:2] == 'HK':
            trip_date = day + ' ' + month
            price = info
            matrix_index = count
            tmp.append([trip_date, price, matrix_index])
        else:
            day = info
            count += 8 if (day == '1' and count != 0) else 1
    return count, tmp

def generate_trip_df(trips, links_names):
    # Generate a pandas dataframe to extract for more analysis
    trip_df = []
    for trip in trips:
        for i in trip['return_options']:
            tmp_dict = {}
            tmp_dict['Departure Date'] = trip['departure_date']
            tmp_dict['Return Date'] = i['return_date']
            tmp_dict['Price HK$'] = int(i['price'].replace(',','')[3:-1])
            trip_df.append(tmp_dict)
    links_names = links_names[len(trip_df)*-3:][1::3]
    trip_df = pd.DataFrame(trip_df)
    trip_df['Return Date'] = pd.to_datetime(trip_df['Return Date'])
    trip_df['Departure Date'] = pd.to_datetime(trip_df['Departure Date'])
    trip_df['Departure Day'] = trip_df['Departure Date'].apply(lambda x : x.strftime("%A"))
    trip_df['Return Day'] = trip_df['Return Date'].apply(lambda x : x.strftime("%A"))
    trip_df['Trip Duration'] = trip_df['Return Date'] - trip_df['Departure Date']
    trip_df['Booking link'] = links_names
    return trip_df

# ########################################################################################
# #/Main/
# ########################################################################################
if __name__ == "__main__":
    valid_destinations = get_airports_data()
    start_code, end_code, duration = get_args(valid_destinations)
    driver = get_driver()

    start_date = datetime.today()
    end_date = start_date + timedelta(weeks = 6)
    visit_website(start_code, end_code, start_date, end_date, duration, driver)
    flights_table = get_flights_table(driver)
    trip_info, start_date = get_departure_info(flights_table, driver)
    trips, links_names = get_return_info(trip_info,driver)
    trip_df = generate_trip_df(trips, links_names)
    trip_df.to_csv(f'./{start_code}-{end_code}_start_date.csv')

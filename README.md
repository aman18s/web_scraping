# web_scraping
This script gets flight information for around 6 weeks.

It starts by getting a list of all internatial airports, their IATA Code and the city name. This is needed to have valid search parameters.

We input the start location, the destination city we want to travel to and the duration of the trip.

It does a flexiable check on the calender i.e. +-3 days max to help find the cheapest trip available on the specific day. It returns the information of the trip and the booking link and more details in a csv file.

This script can be easily expanded to check for a longer duration and multiple destinations. Sample output files have also been attached

Run the script as below example:
python project.py -s "Hong Kong" -e "Toronto (Mississauga)" -d 4

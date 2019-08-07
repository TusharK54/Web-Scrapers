
import time, datetime
from bs4 import BeautifulSoup
from base import DataScraper

class Hot100Scraper(DataScraper):
    """
    A web scraper that can extract and save data from the Billboard website.

    Dataset Features:
    -----------------
        Position (int)          - The rank of the song in the current week
        Title (str)             - The song title
        Artist (str)            - The song artists
        Last Week (int)         - The rank of the song in the previous week
        Peak Position (int)     - The highest rank the song has reached on the Billboard Hot 100 thus far
        Weeks on Chart (int)    - The number of weeks the song has been on the Billboard Hot 100 thus far
        Chart Date (str)        - The Billboard Hot 100 chart week in the format mm-dd-yyyy
    """

    def __init__(self):
        base_url = 'https://www.billboard.com'
        features = ['Position', 'Title', 'Artist', 'Last Week', 'Peak Position', 'Weeks on Chart', 'Chart Date']
        super().__init__(base_url, features)

    def scrape(self, min_date:tuple=None, max_date:tuple=None):
        """
        Extracts data from the Billboard Hot 100 chart for a given range of dates.

        Parameters:
        -----------
        min_date (tuple) - The first week of the Billboard Hot 100 to extract data.
            Formatted (mm, dd, yyyy).
            Latest week by default.
            Note that the first week of Billboard Hot 100 data started on 1958-08-04.
        max_date (tuple) - The last week of the Billboard Hot 100 to extract data
            Formatted (mm, dd, yyyy).        
            Latest week by default.
        """
        total_time, charts_fetched = 0, 0 # Program metadata

        # Extract datetime dates from tuple date parameters
        min_date = datetime.date.today() if min_date is None else datetime.date(min_date[2], min_date[0], min_date[1])
        date = datetime.date.today() if max_date is None else datetime.date(max_date[2], max_date[0], max_date[1])
        date += datetime.timedelta((12 - date.weekday()) % 7) # Gets next Saturday
        if date < min_date: return

        # Extract data from each weekly chart
        week_delta = datetime.timedelta(weeks=1)
        while date >= min_date:
            # Collect program metadata
            charts_fetched += 1
            time_interval = time.time_ns()

            # Get current Billboard Hot 100 page
            delay = self._delay()
            chart_url = self.base_url + '/charts/hot-100/' + date.strftime('%Y-%m-%d')
            page = self.session.get(chart_url)
            if not page: continue
            soup = BeautifulSoup(page.text, 'lxml')

            # Get date of Billboard chart week
            chart_date = soup.find('button', {'class': 'chart-detail-header__date-selector-button'}).contents[0].string.strip()
            chart_date = datetime.datetime.strptime(chart_date, '%B %d, %Y')
            date = datetime.date(chart_date.year, chart_date.month, chart_date.day) - week_delta # Not all chart weeks are based around Saturday

            # Collect song data for current week
            song_list = soup.find_all('div', {'class': 'chart-list-item'})
            song_data = []
            for song in song_list:
                song_info = dict.fromkeys(self.features)
                song_info['Chart Date'] = chart_date.strftime('%m-%d-%Y')
                song_info['Position'] = int(song['data-rank'])
                song_info['Title'] = song['data-title']
                song_info['Artist'] = song['data-artist']

                extra_info = song.find('div', {'class': 'chart-list-item__stats'})
                if extra_info is None: # For songs that are making their debut on the Billboard Hot 100
                    song_info['Last Week'] = None
                    song_info['Peak Position'] = song_info['Position']
                    song_info['Weeks on Chart'] = 1
                else: # For songs that have been on the Billboard Hot 100
                    last_week = extra_info.find('div', {'class': 'chart-list-item__last-week'}).string
                    song_info['Last Week'] = int(last_week) if last_week != '-' else None
                    song_info['Peak Position'] = int(extra_info.find('div', {'class': 'chart-list-item__weeks-at-one'}).string)
                    song_info['Weeks on Chart'] = int(extra_info.find('div', {'class': 'chart-list-item__weeks-on-chart'}).string)
                song_data.append(song_info)

            # Append data
            self.append_rows(song_data)

            # Update program metadata and log
            time_interval = (time.time_ns() - time_interval) * 10**-9 - delay
            total_time += time_interval
            self.logger.info('Scraped chart for the week of ' + date.strftime('%m-%d-%Y') + f' in {round(time_interval, 5)} seconds')

        self.logger.info(f'DONE scraping {charts_fetched} Billboard Hot 100 charts in {round(total_time, 5)} seconds')

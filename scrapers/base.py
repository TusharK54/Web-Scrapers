
from bs4 import BeautifulSoup
import abc, logging, requests, json, pandas as pd
import settings

class Scraper(abc.ABC):
    """Abstract base class for a web crawler that can extract and save data from pages on a website"""

    def __init__(self, base_url:str):
        # Input parameter values
        self.base_url = base_url

        # Settings values - may be overriden by child classes
        self.sleep_interval = settings.SLEEP_INTERVAL

        # Other values
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.valid_file_types = ['csv', 'json', 'html']

    @abc.abstractmethod
    def scrape(self):
        """Extracts data from a website and appends it to the underlying data storage structure"""
        pass

    def write(self, filename, data, features=None) -> str:
        """
        Writes the contents of the 'data' parameter to the file specified by the 'filename' parameter, overwriting it if necessary.
        The optional 'features' parameter specifies which features of the data should be written for applicable file types.
        """
        # Initialize file parameters from settings and keyword arguments
        output_folder       = settings.DATASETS_FOLDER
        encoding            = settings.ENCODING
        delimiter           = settings.DELIMITER
        quotechar           = settings.QUOTECHAR
        default_file_type   = settings.DEFAULT_FILE_TYPE
        if default_file_type not in self.valid_file_types: 
            default_file_type = self.valid_file_types[0]

        # Get file type and change if necessary
        output_file = output_folder + '/' + filename
        type_index = output_file.rfind('.') + 1
        file_type = default_file_type
        if type_index > -1 and output_file[type_index:] in self.valid_file_types:
            file_type = output_file[type_index:]
        else:
            output_file += '.' + file_type

        # Write data to file depending on file type
        if file_type == 'csv':
            df = pd.DataFrame(data, columns=features)
            df.to_csv(output_file, index=False, sep=delimiter, header=True, encoding=encoding, quotechar=quotechar)
        elif file_type == 'json':
            with open(output_file, mode='w', newline='', encoding=encoding) as json_file:
                json.dump(data, json_file, skipkeys=True, indent=2)
        elif file_type == 'html':
            with open(output_file, mode='w', newline='', encoding=encoding) as html_file:
                json.dump(data, html_file, skipkeys=True, indent=2)

        return output_file

    def get_robots_txt(self) -> str:
        """Extracts and returns the robots.txt of the root website if it can be found"""
        self.logger.info('Extracting robots.txt')
        robots_link = self.base_url.strip('/') + '/' + 'robots.txt'
        robots_page = self.session.get(robots_link)
        if robots_page:
            return robots_page.text
        else:
            return ''
  
class DataScraper(Scraper):
    """A web crawler that can extract and save cleaned data from a website in a structured format"""
    
    def __init__(self, base_url:str, features:list):
        super().__init__(base_url)
        self.data = [] # List of dictionaries
        self.features = features
        self.valid_file_types = ['csv', 'json']

    def write(self, filename) -> str:
        """Writes the data extracted by the scraper to the file specified by the 'filename' parameter, overwriting it if necessary."""
        return super().write(filename, self.data, self.features)

    def append_row(self, row:dict):
        """Appends a single row to the underlying dataset structure - row must be a dictionary mapping 'feature':'value'"""
        self.data.append(row)

    def append_rows(self, rows:list):
        """Appends multiple rows to the underlying dataset structure - rows must be a list of dictionaries mapping 'feature':'value'"""
        self.data += rows 

    def get_dataframe(self) -> pd.DataFrame():
        """Returns the data extracted by the scraper in a pandas DataFrame object"""
        return pd.DataFrame(self.data, columns=self.features)

class WebScraper(Scraper):
    """A web crawler that can extract and save the HTML of a website"""

    def __init__(self, base_url:str):
        super().__init__(base_url)
        self.html = ''
        self.valid_file_types = ['html']

    def write(self, filename) -> str:
        """Writes the HTML extracted by the scraper to the file specified by the 'filename' parameter, overwriting it if necessary."""
        return super().write(filename, self.html)

if __name__ == "__main__":
    pass
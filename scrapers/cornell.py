
import time
from bs4 import BeautifulSoup
from base import DataScraper

class CornellCoursesScraper(DataScraper):
    """
    A web scraper that can extract and save data from the Cornell Course Roster website.
    
    Dataset Features (all str types):
    ---------------------------------
        Code                    - Subject code and course number
        Title                   - Name of course
        Credits                 - Number of credits (may be a range)
        Grading                 - Grading type
        Semesters Offered       - Which semesters the course is offered
        Prerequisites           - 
        Corequisites            - 
        Crosslisted             - 
        Distribution Category   - 
        Breadth Requirement     -
        Forbidden Overlap       -
        Description             - 
    """

    def __init__(self):
        base_url = 'https://classes.cornell.edu'
        features = ['Code', 'Title', 'Credits', 'Grading', 'Semesters Offered', 'Prerequisites', 'Corequisites', 'Crosslisted', 'Distribution Category', 'Breadth Requirement', 'Forbidden Overlap', 'Description']
        super().__init__(base_url, features)
        self.sleep_interval = 0

    def scrape(self, semester:str, subjects:list=None):
        """
        Extracts data from the Cornell Course Roster for a given list of subjects.

        Parameters:
        semester (str) - Semester name to scrape course roster data from.
            Must be in the format '{SE}{YR}', where SE must be FA, WI, SP, or SU for the season 
            and YR is the last 2 digits of the year.
            Ex. Fall 2019 semester is given by 'FA19'
        subjects (list) - List of subject codes
            Get all listed subjects by default
        """
        total_time = 0

        # Validate input parameters
        semester = semester.upper()
        if semester[:2] not in ('FA', 'WI', 'SP', 'SU'):
            raise ValueError(semester + " is not a valid semester value - must start with either 'FA', 'WI', 'SP', or 'SU' (see docs for more details)")
        elif not semester[2:].isdecimal or len(semester) != 4:
            raise ValueError(semester + ' is not a valid semester value - must end in the last 2 digits of the year (see docs for more details)')

        # Get dictionary of subject page links
        page = self.session.get(self.base_url + '/browse/roster/' + semester)
        if not page:
            raise ValueError(page.url + ' page not found - check that ' + semester + ' is a valid semester (see docs for more details)')
        soup = BeautifulSoup(page.text, 'lxml')
        raw_subjects = soup.find_all('li', {'class': 'browse-subjectcode'})
        subject_links = {subject.string.strip() : subject.contents[0]['href'] for subject in raw_subjects}    
        if subjects is not None:
            subject_links = {subject_code.upper() : subject_links[subject_code.upper()] for subject_code in subjects}
        
        # Get list of course page links
        course_links = []
        for iteration, subject in enumerate(subject_links.keys()):
            time_interval = time.time_ns()

            page = self.session.get(self.base_url + subject_links[subject])
            soup = BeautifulSoup(page.text, 'lxml')

            raw_courses = soup.find_all('div', {'class': 'title-coursedescr'})
            course_links += [course.contents[0]['href'] for course in raw_courses]
            
            # Update program metadata and log
            time_interval = (time.time_ns() - time_interval) * 10**-9
            total_time += time_interval
            log_spacer1, log_spacer2 = '.' * (3 + (5 - len(subject))), '.' * (3 + (7 - len(str(round(time_interval, 5)))))
            self.logger.info(f'Scraped {subject} subject page {log_spacer1} in {round(time_interval, 5)} seconds {log_spacer2} {len(subject_links)-(iteration+1)} subjects remaining')
            
        # Extract data from each course link
        for iteration, course_link in enumerate(course_links):
            # Collect program metadata
            time_interval = time.time_ns()

            # Get current course page 
            page = self.session.get(self.base_url + course_link)
            soup = BeautifulSoup(page.text, 'lxml')

            # Data that is always available and readily acessible
            course_info = dict.fromkeys(self.features)
            course_info['Code'] = soup.find('div', {'class': 'title-subjectcode'}).get_text()
            course_info['Title'] = soup.find('div', {'class': 'title-coursedescr'}).get_text()
            course_info['Description'] = soup.find('p', {'class': 'catalog-descr'}).get_text()
            
            # Data that is always available in enrollment info section
            enrollment_info = soup.find('ul', {'class': 'enroll-header'})
            enrollment_header = enrollment_info.find('li', {'class': 'enroll-info'}).get_text()
            course_info['Credits'] = enrollment_info.find('span', {'class': 'credit-val'}).get_text()
            course_info['Grading'] = enrollment_info.find('span', {'class': 'tooltip-iws'}).contents[0].string
            if 'Combined with:' in enrollment_header:
                crosslisted_index = enrollment_header.index('Combined with:') + len('Combined with:')
                course_info['Crosslisted'] = enrollment_header[crosslisted_index:]

            # Data that isn't always available
            requisites_info = soup.find('span', {'class': 'catalog-prereq'})
            if requisites_info:
                requisites_text = requisites_info.contents[1].string.replace(u'\xa0', ' ')
                if 'Prerequisite:' in requisites_text and 'Corequisite:' in requisites_text:
                    prerequisite_index = requisites_text.index('Prerequisite')
                    corequisite_index = requisites_text.index('Corequisite')
                    course_info['Prerequisites'] = requisites_text[prerequisite_index+len('Prerequisite:'):corequisite_index]
                    course_info['Corequisites'] = requisites_text[corequisite_index+len('Corequisite:'):]
                elif 'Prerequisite:' in requisites_text:
                    course_info['Prerequisites'] = requisites_text[len('Prerequisite:'):]
                elif 'Corequisite:' in requisites_text:
                    course_info['Corequisites'] = requisites_text[len('Corequisite:'):]

            semesters_info = soup.find('span', {'class': 'catalog-when-offered'})
            if (semesters_info):
                course_info['Semesters Offered'] = semesters_info.contents[1].string

            distribution_info = soup.find('span', {'class': 'catalog-distr'})
            if distribution_info:
                course_info['Distribution Category'] = distribution_info.contents[1]

            forbidden_info = soup.find('span', {'class': 'catalog-forbid'})
            if (forbidden_info):
                forbidden_text = forbidden_info.contents[1].string
                course_info['Forbidden Overlap'] = forbidden_text[len('Forbidden Overlap:'):]

            breadth_info = soup.find('span', {'class': 'catalog-breadth'})
            if breadth_info:
                course_info['Breadth Requirement'] = breadth_info.contents[1]

            # Clean and append data
            preprocess_value = lambda x: x.replace('\n', '  ').strip('.: ')
            clean_course_info = {key: preprocess_value(course_info[key]) for key in course_info if course_info[key]}
            self.append_row(clean_course_info)

            # Update program metadata and log
            time_interval = (time.time_ns() - time_interval) * 10**-9
            total_time += time_interval
            log_spacer1, log_spacer2 = '.' * (1 + (10 - len(course_info["Code"]))), '.' * (3 + (7 - len(str(round(time_interval, 5)))))
            self.logger.info(f'Scraped {course_info["Code"]} course page {log_spacer1} in {round(time_interval, 5)} seconds {log_spacer2} {len(course_links)-(iteration+1)} courses remaining')

        self.logger.info(f'DONE scraping {len(course_links)} courses in {round(total_time, 5)} seconds')

import requests, time, csv, sys
from bs4 import BeautifulSoup

datasets_folder = 'datasets'

def scrape_subjects(semester:str, subjects:list=[], data_file='cornell_courses.csv'):
    """
    Extracts data from the Cornell Course Roster for a given list of subjects.

    Parameters:
    semester (str)              - Semester name to scrape course roster data from.
                                    ~ Must be in the format '{SE}{YR}', where SE can either be FA, WI, SP, or SU for the season
                                      and YR is the last 2 digits of the year.
                                    ~ Ex. Fall 2019 semester is given by 'FA19'
    subjects (list)             - List of subject codes
                                    ~ Get all listed subjects by default
    data_file (str)             - A .csv file name to store the extracted data; will be overwritten if it already exists.
                                    ~ If the file does not end in '.csv', it will be appended to the file name
                                    ~ 'cornell_courses.csv' by default

    Dataset Features:
    Code (str)                  - Subject code and course number
    Title (str)                 - Name of course
    Credits (str)               - Number of credits (may be a range)
    Grading (str)               - Grading type
    Semesters Offered (str)     - Which semesters the course is offered
    Prerequisites (str)         - 
    Corequisites (str)          - 
    Crosslisted (str)           - 
    Distribution Category (str) - 
    Breadth Requirement (str)   -
    Forbidden Overlap (str)     -
    Description (str)           - 
    """

    base_url = 'https://classes.cornell.edu'
    features = ['Code', 'Title', 'Credits', 'Grading', 'Semesters Offered', 'Prerequisites', 'Corequisites', 'Crosslisted', 'Distribution Category', 'Breadth Requirement', 'Forbidden Overlap', 'Description']
    total_time = 0
    
    # Get list of subject page links
    session = requests.Session()
    page = session.get(base_url + '/browse/roster/' + semester)
    if not page:
        raise ValueError(semester + ' is not a valid semester value - must be in the form {SE}{YR}. See function documentation for more details.')
    soup = BeautifulSoup(page.text, 'lxml')
    raw_subjects = soup.find_all('li', {'class': 'browse-subjectcode'})
    subject_links = {subject.string.strip() : subject.contents[0]['href'] for subject in raw_subjects}    
    if subjects:
        subjects = [subject.upper() for subject in subjects]
        subject_links = {subject_code : subject_links[subject_code] for subject_code in subjects}
    
    # Get list of course page links
    course_links = []
    iteration = 0
    for subject in subject_links.keys():
        print('Scraping', subject, 'subject page', '.' * (3+5-len(subject)), end=' ')
        sys.stdout.flush()
        time_interval = time.time_ns()
        iteration += 1

        page = session.get(base_url + subject_links[subject])
        soup = BeautifulSoup(page.text, 'lxml')

        raw_courses = soup.find_all('div', {'class': 'title-coursedescr'})
        course_links += [course.contents[0]['href'] for course in raw_courses]
        
        # Update program metadata
        time_interval = (time.time_ns() - time_interval) * 10**-9
        total_time += time_interval
        print('done in', round(time_interval, 5), 'seconds', '.' * (3+7-len(str(round(time_interval, 5)))), len(subject_links) - iteration, 'subjects remaining')
        
    # Extract data from each course link
    if data_file[-4:] != '.csv': data_file += '.csv'
    global datasets_folder
    with open(f'{datasets_folder}/{data_file}', mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, features)
        writer.writeheader()

        iteration = 0
        for course_link in course_links:
            # Collect program metadata
            time_interval = time.time_ns()
            iteration += 1

            # Get current course page 
            print('Fetching course data', end=' ')
            page = session.get(base_url + course_link)
            soup = BeautifulSoup(page.text, 'lxml')

            # Data that is always available and readily acessible
            course_info = dict.fromkeys(features)
            course_info['Code'] = soup.find('div', {'class': 'title-subjectcode'}).get_text()
            course_info['Title'] = soup.find('div', {'class': 'title-coursedescr'}).get_text()
            course_info['Description'] = soup.find('p', {'class': 'catalog-descr'}).get_text()
            print('for', course_info['Code'], '.' * (3+9-len(course_info['Code'])), end=' ')
            sys.stdout.flush()
            
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

            # Clean and append data to CSV
            clean_string = lambda x: x.replace('\n', '  ').strip('.: ')
            clean_course_info = {key: clean_string(course_info[key]) for key in course_info if course_info[key]}
            writer.writerow(clean_course_info)

            # Update program metadata
            time_interval = (time.time_ns() - time_interval) * 10**-9
            total_time += time_interval
            print('done in', round(time_interval, 5), 'seconds', '.' * (3+7-len(str(round(time_interval, 5)))), len(course_links) - iteration, 'courses remaining')

    print('DONE; fetched data for', len(course_links), 'course{s} in'.format(s='' if len(course_links) == 1 else 's'), round(total_time, 5), 'seconds.')
    return data_file

if __name__ == "__main__":
    pass
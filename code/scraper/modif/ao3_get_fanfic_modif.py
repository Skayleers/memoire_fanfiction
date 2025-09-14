######
#
# This script takes in (a list or csv of) fic IDs and
# writes a csv containing the fic itself, as well as the
# metadata.
#
# Usage - python ao3_get_fanfics.py ID [--header header] [--csv csvoutfilename]
#
# ID is a required argument. It is either a single number,
# multiple numbers seperated by spaces, or a csv filename where
# the IDs are the first column.
# (It is suggested you run ao3_work_ids.py first to get this csv.)
#
# --header is an optional string which specifies your HTTP header
# for ethical scraping. For example, the author's would be
# 'Chrome/52 (Macintosh; Intel Mac OS X 10_10_5); Jingyi Li/UC Berkeley/email@address.com'
# If left blank, no header will be sent with your GET requests.
#
# --csv is an optional string which specifies the name of your
# csv output file. If left blank, it will be called "fanfics.csv"
# Note that by default, the script appends to existing csvs instead of overwriting them.
#
# --restart is an optional string which when used in combination with a csv input will start
# the scraping from the given work_id, skipping all previous rows in the csv
#
# --bookmarks is an optional flag which collects the users who have bookmarked a fic.
# Because this is a slow operation, it is excluded by default.
#
# --firstchap is an optional flag which, when set, only pulls the first chapter instead
# of all chapters.
#
# --metadata-only is an optional flag which pulls the metadata but not the content.
# default is off (i.e. default includes the fic contents). This also implies --firstchap
#
# Author: Jingyi Li soundtracknoon [at] gmail
# I wrote this in Python 2.7. 9/23/16
# Updated 2/13/18 (also Python3 compatible)
#
#
# Update 2/3/21
# jack-debug
# I added a new argument that only gets fanfics of a certain language
# --lang
#######
import requests
from bs4 import BeautifulSoup
import argparse
import time
import os
import csv
import sys
from unidecode import unidecode
import random

# seconds to wait between page requests
delay = 5
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS_8MSR; rv:11.0) like Gecko",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Android 14; Mobile; rv:138.0) Gecko/138.0 Firefox/138.0"
]

def get_random_user_agent():
    return random.choice(user_agents)

def get_tag_info(category, meta):
    '''
    given a category and a 'work meta group, returns a list of tags (eg, 'rating' -> 'explicit')
    '''
    try:
        tag_list = meta.find("dd", class_=str(category) + ' tags').find_all(class_="tag")
    except AttributeError as e:
        return []
    return [unidecode(result.text) for result in tag_list]


def get_stats(meta):
    '''
    returns a list of
    language, published, status, date status, words, chapters, comments, kudos, bookmarks, hits
    '''
    categories = ['language', 'published', 'status', 'words', 'chapters', 'comments', 'kudos', 'bookmarks', 'hits']

    stats = list(map(lambda category: meta.find("dd", class_=category), categories))

    if not stats[2]:
        stats[2] = stats[1]  # no explicit completed field -- one shot
    try:
        stats = [unidecode(stat.text) for stat in stats]
    except AttributeError as e:  # for some reason, AO3 sometimes miss stat tags (like hits)
        new_stats = []
        for stat in stats:
            if stat:
                new_stats.append(unidecode(stat.text))
            else:
                new_stats.append('null')
        stats = new_stats

    stats[0] = stats[0].rstrip().lstrip()  # language has weird whitespace characters
    # add a custom completed/updated field
    status = meta.find("dt", class_="status")
    if not status:
        status = 'Completed'
    else:
        status = status.text.strip(':')
    stats.insert(2, status)

    return stats


def get_tags(meta):
    '''
    returns a list of lists, of
    rating, category, fandom, pairing, characters, additional_tags
    '''
    tags = ['rating', 'category', 'fandom', 'relationship', 'character', 'freeform']
    return list(map(lambda tag: get_tag_info(tag, meta), tags))


# get kudos
def get_kudos(meta):
    if (meta):
        users = []
        ## hunt for kudos' contents
        kudos = meta.contents

        # extract user names
        for kudo in kudos:
            if kudo.name == 'a':
                if 'more users' not in kudo.contents[0] and '(collapse)' not in kudo.contents[0]:
                    users.append(kudo.contents[0])

        return users
    return []


# get author(s)
def get_authors(meta):
    tags = meta.contents
    authors = []

    for tag in tags:
        if tag.name == 'a':
            authors.append(tag.contents[0])

    return authors


# get bookmarks by page
def get_bookmarks(url, header_info):
    bookmarks = []
    headers = {'user-agent': get_random_user_agent()}

    req = requests.get(url, headers=headers)
    src = req.text

    time.sleep(delay)
    soup = BeautifulSoup(src, 'html.parser')

    sys.stdout.write('scraping bookmarks ')
    sys.stdout.flush()

    # find all pages
    if (soup.find('ol', class_='pagination actions')):
        pages = soup.find('ol', class_='pagination actions').findChildren("li", recursive=False)
        max_pages = int(pages[-2].contents[0].contents[0])
        count = 1

        sys.stdout.write('(' + str(max_pages) + ' pages)')
        sys.stdout.flush()

        while count <= max_pages:
            # extract each bookmark per user
            tags = soup.findAll('h5', class_='byline heading')
            bookmarks += get_users(tags)

            # next page
            count += 1
            req = requests.get(url + '?page=' + str(count), headers=headers)
            src = req.text
            soup = BeautifulSoup(src, 'html.parser')
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(delay)
    else:
        tags = soup.findAll('h5', class_='byline heading')
        bookmarks += get_users(tags)

    print('')
    return bookmarks


# get users form bookmarks
def get_users(meta):
    users = []
    for tag in meta:
        user = tag.findChildren("a", recursive=False)[0].contents[0]
        users.append(user)

    return users


def access_denied(soup):
    if (soup.find(class_="flash error")):
        return True
    if (not soup.find(class_="work meta group")):
        return True
    return False


def write_fic_to_csv(fic_id, only_first_chap, lang, include_bookmarks, metadata_only, writer, errorwriter, header_info=''):
    '''
    fic_id is the AO3 ID of a fic, found every URL /works/[id].
    writer is a csv writer object
    the output of this program is a row in the CSV file containing all metadata
    and the fic content itself (excludes content if metadata_only=True).
    header_info should be the header info to encourage ethical scraping.
    '''
    print(f"Scraping {fic_id}...")
    url = f'http://archiveofourown.org/works/{fic_id}?view_adult=true'
    if not (only_first_chap or metadata_only):
        url += '&amp;view_full_work=true'

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        headers = {'user-agent': header_info}
        req = requests.get(url, headers=headers)
        status = req.status_code

        if status == 200:
            break

        if status == 429:
            print(f"Erreur 429 : tentative {attempt}/{max_retries}, attente 60 sec...")
            time.sleep(60)
        else:
            print(f"Erreur {status} : tentative {attempt}/{max_retries}, attente 30 sec...")
            time.sleep(30)

    if status >= 400:
        print(f"❌ Échec après {max_retries} tentatives. Fic {fic_id} ignorée.")
        errorwriter.writerow([fic_id, status])
        return False  # Signale un échec

    soup = BeautifulSoup(req.text, 'html.parser')
    if access_denied(soup):
        print('Access Denied')
        errorwriter.writerow([fic_id, 'Access Denied'])
        return False

    meta = soup.find("dl", class_="work meta group")
    author = get_authors(soup.find("h3", class_="byline heading"))
    tags = get_tags(meta)
    stats = get_stats(meta)
    title = unidecode(soup.find("h2", class_="title heading").string).strip()
    visible_kudos = get_kudos(soup.find('p', class_='kudos'))
    hidden_kudos = get_kudos(soup.find('span', class_='kudos_expanded hidden'))
    all_kudos = visible_kudos + hidden_kudos

    if lang and lang != stats[0]:
        print(f"Fic non en {lang}, ignorée.")
        return False

    all_bookmarks = get_bookmarks(f'http://archiveofourown.org/works/{fic_id}/bookmarks', header_info) if include_bookmarks else []

    if not metadata_only:
        content = soup.find("div", id="chapters")
        chapters = content.select('p')
        chaptertext = '\n\n'.join([unidecode(chapter.text) for chapter in chapters])
    else:
        chaptertext = ""

    row = [fic_id, title, author] + [', '.join(tag) for tag in tags] + stats + [all_kudos, all_bookmarks, chaptertext]

    try:
        writer.writerow(row)
        print("✅ Fic collectée avec succès.")
        return True  # Signale un succès
    except Exception as e:
        print(f"❌ Erreur d’écriture pour {fic_id}: {e}")
        errorwriter.writerow([fic_id, str(e)])
        return False  # Signale un échec



def get_args():
    parser = argparse.ArgumentParser(description='Scrape and save some fanfic, given their AO3 IDs.')
    parser.add_argument(
        'ids', metavar='IDS', nargs='+',
        help='a single id, a space seperated list of ids, or a csv input filename')
    parser.add_argument(
        '--csv', default='fanfics.csv',
        help='csv output file name')
    parser.add_argument(
        '--header', default='',
        help='user http header')
    parser.add_argument(
        '--restart', default='',
        help='work_id to start at from within a csv')
    parser.add_argument(
        '--firstchap', default='',
        help='only retrieve first chapter of multichapter fics')
    parser.add_argument(
        '--lang', default='',
        help='only retrieves fics of certain language (e.g English), make sure you use correct spelling and capitalization or this argument will not work')
    parser.add_argument(
        '--bookmarks', action='store_true',
        help='retrieve bookmarks; ')
    parser.add_argument(
        '--metadata-only', action='store_true',
        help='only retrieve metadata')
    args = parser.parse_args()
    fic_ids = args.ids
    is_csv = (len(fic_ids) == 1 and '.csv' in fic_ids[0])
    csv_out = str(args.csv)
    headers = str(args.header)
    restart = str(args.restart)
    ofc = str(args.firstchap)
    lang = str(args.lang)
    include_bookmarks = args.bookmarks
    metadata_only = args.metadata_only
    if ofc != "":
        ofc = True
    else:
        ofc = False
    if lang == "":
        lang = False
    return fic_ids, csv_out, headers, restart, is_csv, ofc, lang, include_bookmarks, metadata_only


'''

'''


def process_id(fic_id, restart, found):
    if found:
        return True
    if fic_id == restart:
        return True
    else:
        return False


def main():
    fic_ids, csv_out, headers, restart, is_csv, only_first_chap, lang, include_bookmarks, metadata_only = get_args()
    os.chdir(os.getcwd())

    output_directory = os.path.dirname(csv_out)
    if output_directory and not os.path.isdir(output_directory):
        print("Creating output directory " + output_directory)
        os.mkdir(output_directory)

    with open(csv_out, 'a', newline="") as f_out:
        writer = csv.writer(f_out)
        with open(os.path.join(os.path.dirname(csv_out), "errors_" + os.path.basename(csv_out)), 'a', newline="") as e_out:
            errorwriter = csv.writer(e_out)

            # Vérification si le fichier CSV a une en-tête
            if os.stat(csv_out).st_size == 0:
                print('Writing a header row for the csv.')
                header = ['work_id', 'title', 'author', 'rating', 'category', 'fandom', 'relationship', 'character',
                          'additional tags', 'language', 'published', 'status', 'status date', 'words', 'chapters',
                          'comments', 'kudos', 'bookmarks', 'hits', 'all_kudos', 'all_bookmarks', 'body']
                writer.writerow(header)

            # Compteur pour afficher la progression
            total_fics = 0
            if is_csv:
                with open(fic_ids[0], 'r', newline="") as f_in:
                    total_fics = sum(1 for _ in csv.reader(f_in))  # Compter le nombre total de lignes

            elif fic_ids:
                total_fics = len(fic_ids)  # Si on donne une liste d’IDs directement

            processed_fics = 0  # Fanfics traitées
            failed_fics = 0  # Nombre d'échecs

            if is_csv:
                csv_fname = fic_ids[0]
                with open(csv_fname, 'r+', newline="") as f_in:
                    reader = csv.reader(f_in)
                    found_restart = False if restart else True

                    for row in reader:
                        if not row:
                            continue

                        found_restart = process_id(row[0], restart, found_restart)
                        if found_restart:
                            processed_fics += 1
                            print(f"Fanfiction {processed_fics}/{total_fics} en cours...")
                            success = write_fic_to_csv(row[0], only_first_chap, lang, include_bookmarks, metadata_only, writer, errorwriter, headers)
                            if not success:
                                failed_fics += 1

                            time.sleep(delay)
                        else:
                            print('Skipping already processed fic')

            else:
                for fic_id in fic_ids:
                    processed_fics += 1
                    print(f"Fanfiction {processed_fics}/{total_fics} en cours...")
                    success = write_fic_to_csv(fic_id, only_first_chap, lang, include_bookmarks, metadata_only, writer, errorwriter, headers)
                    if not success:
                        failed_fics += 1

                    time.sleep(delay)

            print(f"\n✅ Collecte terminée : {processed_fics} fanfictions traitées.")
            print(f"❌ Nombre de fanfictions échouées : {failed_fics}")



main()

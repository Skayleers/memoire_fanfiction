# Retrieve fic ids from an AO3 search
# Will return in searched order
# Saves ids to a csv for later use e.g. to retrieve fic text

# Options:
# Only retrieve multichapter fics
# Modify search to include a list of tags
#      (e.g. you want all fics tagged either "romance" or "fluff")

from bs4 import BeautifulSoup
import re
import time
import requests
import csv
import sys
import datetime
import argparse
import os

page_empty = False
base_url = ""
url = ""
num_requested_fic = 0
num_recorded_fic = 0
csv_name = ""
multichap_only = ""
tags = []

# keep track of all processed ids to avoid repeats:
# this is separate from the temporary batch of ids
# that are written to the csv and then forgotten
seen_ids = set()


#
# Ask the user for:
# a url of a works listed page
# e.g.
# https://archiveofourown.org/works?utf8=%E2%9C%93&work_search%5Bsort_column%5D=word_count&work_search%5Bother_tag_names%5D=&work_search%5Bquery%5D=&work_search%5Blanguage_id%5D=&work_search%5Bcomplete%5D=0&commit=Sort+and+Filter&tag_id=Harry+Potter+-+J*d*+K*d*+Rowling
# https://archiveofourown.org/tags/Harry%20Potter%20-%20J*d*%20K*d*%20Rowling/works?commit=Sort+and+Filter&page=2&utf8=%E2%9C%93&work_search%5Bcomplete%5D=0&work_search%5Blanguage_id%5D=&work_search%5Bother_tag_names%5D=&work_search%5Bquery%5D=&work_search%5Bsort_column%5D=word_count
# how many fics they want
# what to call the output csv
#
# If you would like to add additional search terms (that is should contain at least one of, but not necessarily all of)
# specify these in the tag csv, one per row.

def get_args():
    global base_url
    global url
    global csv_name
    global num_requested_fic
    global multichap_only
    global tags

    parser = argparse.ArgumentParser(description='Scrape AO3 work IDs given a search URL')
    parser.add_argument(
        'url', metavar='URL',
        help='a single URL pointing to an AO3 search page')
    parser.add_argument(
        '--out_csv', default='work_ids',
        help='csv output file name')
    parser.add_argument(
        '--header', default='',
        help='user http header')
    parser.add_argument(
        '--num_to_retrieve', default='a',
        help='how many fic ids you want')
    parser.add_argument(
        '--multichapter_only', default='',
        help='only retrieve ids for multichapter fics')
    parser.add_argument(
        '--tag_csv', default='',
        help='provide an optional list of tags; the retrieved fics must have one or more such tags')

    args = parser.parse_args()
    url = args.url
    csv_name = str(args.out_csv)

    # defaults to all
    if (str(args.num_to_retrieve) == 'a'):
        num_requested_fic = -1
    else:
        num_requested_fic = int(args.num_to_retrieve)

    multichap_only = str(args.multichapter_only)
    if multichap_only != "":
        multichap_only = True
    else:
        multichap_only = False

    tag_csv = str(args.tag_csv)
    if (tag_csv):
        with open(tag_csv, "r") as tags_f:
            tags_reader = csv.reader(tags_f)
            for row in tags_reader:
                tags.append(row[0])

    header_info = str(args.header)

    return header_info


#
# navigate to a works listed page,
# then extract all work ids
#
def get_ids(header_info='', max_retries=3, delay=2):
    global page_empty
    global seen_ids

    page_number = 1
    page_key = "page="
    start = url.find(page_key)
    if start != -1:
        page_start_index = start + len(page_key)
        page_end_index = url.find("&", page_start_index)
        if page_end_index != -1:
            page_number = int(url[page_start_index:page_end_index])
        else:
            page_number = int(url[page_start_index:])

    print(f"\n[INFO] Récupération des fanfictions à partir de la page {page_number} de l'URL : {url}")

    retries = 0
    works = []

    # Essayer plusieurs fois en cas d'échec
    while retries < max_retries:
        try:
            headers = {'user-agent': header_info}
            req = requests.get(url, headers=headers)

            # Si le serveur répond par le code 429 (limite de requêtes atteinte), on attend et on réessaie
            while req.status_code == 429:
                print("Réponse 429 reçue, réessayer après un délai...")
                time.sleep(10)  # Attente prolongée pour la réponse 429
                req = requests.get(url, headers=headers)

            soup = BeautifulSoup(req.text, "lxml")

            # Recherche des fanfictions sur la page
            works = soup.select("li.work.blurb.group")

            print(f"[INFO] Page actuelle : {url} - Nombre de fanfictions récupérées : {len(works)}")

            if len(works) > 0:
                break

            else:
                print(f"[INFO] Aucune fanfiction trouvée sur cette page. Essai {retries + 1}/{max_retries}.")
                retries += 1
                time.sleep(delay)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Erreur de requête sur la page {url}: {e}")
            retries += 1
            time.sleep(delay)

    if retries == max_retries and len(works) == 0:
        print(f"[INFO] Échec après {max_retries} tentatives. La page {url} semble vide.")
        page_empty = True

    ids = []
    for idx, tag in enumerate(works, start=1):
        t = tag.get('id')[5:]

        print(f"[INFO] Récupération de l'ID {t} (Fanfiction {idx} sur la page {page_number})")

        if t not in seen_ids:
            ids.append(t)
            seen_ids.add(t)
            print(f"[SUCCÈS] L'ID {t} a été ajouté à la liste.")
        else:
            print(f"[DUPLICATA] L'ID {t} a déjà été collecté, ignoré.")

    return ids


#
# update the url to move to the next page
# note that if you go too far, ao3 won't error,
# but there will be no works listed
#
def update_url_to_next_page():
    global url
    key = "page="
    start = url.find(key)

    # there is already a page indicator in the url
    if (start != -1):
        # find where in the url the page indicator starts and ends
        page_start_index = start + len(key)
        page_end_index = url.find("&", page_start_index)
        # if it's in the middle of the url
        if (page_end_index != -1):
            page = int(url[page_start_index:page_end_index]) + 1
            url = url[:page_start_index] + str(page) + url[page_end_index:]
        # if it's at the end of the url
        else:
            page = int(url[page_start_index:]) + 1
            url = url[:page_start_index] + str(page)

    # there is no page indicator, so we are on page 1
    else:
        # there are other modifiers
        if (url.find("?") != -1):
            url = url + "&page=2"
        # there an no modifiers yet
        else:
            url = url + "?page=2"


# modify the base_url to include the new tag, and save to global url
def add_tag_to_url(tag):
    # global url
    # key = "&work_search%5Bother_tag_names%5D="
    # if (base_url.find(key)):
    #     start = base_url.find(key) + len(key)
    #     new_url = base_url[:start] + tag + "%2C" + base_url[start:]
    #     url = new_url
    # else:
    #     url = base_url + "&work_search%5Bother_tag_names%5D=" + tag
    #
    #
    global url
    key = "&work_search%5Bother_tag_names%5D="

    # Encode le tag pour l'inclure correctement dans l'URL
    tag_encoded = requests.utils.quote(tag)

    # Si l'URL contient déjà le paramètre de tag, ajoute le nouveau tag
    if (base_url.find(key) != -1):
        start = base_url.find(key) + len(key)
        new_url = base_url[:start] + tag_encoded + "%2C" + base_url[start:]
        url = new_url
    else:
        url = base_url + key + tag_encoded


#
# after every page, write the gathered ids
# to the csv, so a crash doesn't lose everything.
# include the url where it was found,
# so an interrupted search can be restarted
#
def write_ids_to_csv(ids):
    global num_recorded_fic
    with open(csv_name + ".csv", 'a', newline="") as csvfile:
        wr = csv.writer(csvfile, delimiter=',')
        for id in ids:
            if (not_finished()):
                wr.writerow([id, url])
                num_recorded_fic = num_recorded_fic + 1
            else:
                break


#
# if you want everything, you're not done
# otherwise compare recorded against requested.
# recorded doesn't update until it's actually written to the csv.
# If you've gone too far and there are no more fic, end.
#
def not_finished():
    if (page_empty):
        return False

    if (num_requested_fic == -1):
        return True
    else:
        if (num_recorded_fic < num_requested_fic):
            return True
        else:
            return False


#
# include a text file with the starting url,
# and the number of requested fics
#
def make_readme():
    with open(csv_name + "_readme.txt", "w") as text_file:
        text_file.write(
            "url: " + url + "\n" + "num_requested_fic: " + str(num_requested_fic) + "\n" + "retreived on: " + str(
                datetime.datetime.now()))


# reset flags to run again
# note: do not reset seen_ids
def reset():
    global page_empty
    global num_recorded_fic
    page_empty = False
    num_recorded_fic = 0


def process_for_ids(header_info=''):
    while (not_finished()):
        # 5 second delay between requests as per AO3's terms of service
        time.sleep(5)
        ids = get_ids(header_info)
        write_ids_to_csv(ids)
        update_url_to_next_page()


def load_existing_ids():
    global seen_ids

    if (os.path.exists(csv_name + ".csv")):
        print("skipping existing IDs...\n")
        with open(csv_name + ".csv", 'r') as csvfile:
            id_reader = csv.reader(csvfile)
            for row in id_reader:
                seen_ids.add(row[0])
    else:
        print("no existing file; creating new file...\n")


def main():
    header_info = get_args()
    make_readme()

    print("Chargement des IDs existants si présents...\n")
    load_existing_ids()

    print("Démarrage de la collecte des fanfictions...\n")

    # Si des tags sont fournis, récupérer les fanfictions pour chaque tag
    if len(tags):
        for t in tags:
            print(f"[INFO] Récupération des fanfictions pour le tag : {t}")
            reset()  # Réinitialise les variables de collecte pour chaque tag
            add_tag_to_url(t)  # Modifie l'URL pour inclure le tag
            process_for_ids(header_info)  # Collecte des fanfictions avec la nouvelle URL
    else:
        process_for_ids(header_info)

    print("Collecte terminée.")



main()

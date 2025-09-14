# memoire_fanfiction

Ce dépôt contient les ressources utilisées dans le cadre de mon mémoire de master portant sur l'analyse lexicale et stylométrique de cinq tags de fanfictions. L’objectif de ce travail était d’explorer les spécificités linguistiques propres à chaque tag à l’aide d’outils de traitement automatique du langage, et de tester leur reconnaissance via des méthodes de classification supervisée.

## Note
Les noms des cinq tags étudiés sont souvent mentionnés dans les différents fichiers de ce dépôts et sont souvent présents dans les noms de ces fichiers sous formes abrégées :
- angst pour *Angst*
- fluff pour *Fluff*
- hc ou H/C pour *Hurt/Comfort*
- flt pour *Friends to lovers*
- etl pour *Enemies to lovers*

## Utilisation de l'IA
Certaines parties de code ont été réalisées avec l’aide d’outils d’intelligence artificielle mais sont toujours relues et validées avant d'être incluses dans les fichiers du mémoire.

## Contenu du dépôt
### code
Le dossier "code" contient tous les scripts et portions de code générées et utilisées pour mener à bien ce mémoire.

Il est divisé en quatre sous-dossiers : classification, pydistinto, recup_txt_pydistinto et scraper.

#### *scraper*
Ce sous-dossier contient les scripts qui ont permis la collecte des fanfictions depuis le site d'ao3.org.

Il y a deux sous-dossiers à l'intérieur :
- original : contient les scripts originaux récupérés sur le GitHub radiolarian/AO3Scraper (https://github.com/radiolarian/AO3Scraper)
    - ao3_work_ids.py : permet de collecter les identifiants des fanfictions voulues
    - ao3_get_fanfics.py : permet de collecter les fanfictions à l'aide des identifiants préalablement collectés
- modif : contient les scripts modifiés pour les besoins du mémoire
    - ao3_ids_modif.py : pour récupérer les identifiants
    - ao3_get_fanfic_modif.py : pour collecter les fanfictions

#### *classification*
Ce sous-dossier contient tous les scripts qui ont permis de réaliser la classifiaction automatique des fanfictions collectées à l'aide d'algorithmes classiques.

A l'intérieur on retrouve deux sous-dossiers :
-pretraitements : contient tous les scripts des différents prétraitements réalisés sur les données afin de les préparer à la classification automatique
    - 01_preparation&fusion.ipynb : fusion des différents CSV crées lors de la collecte contenant chacun les données d'un tag en un seul fichiers CSV contenant les données de tous les tags (+ premiers ajustements (suppression de doublons, ajout de colonnes nécessaires))
    - 02_nettoyage&taille.ipynb : nettoyage des textes et limite maximale de longueur
    - 03_personnages.ipynb : création d'un colonne contenant les textes des fanfictions sans les noms des personnages
    - 04_tokenisation.ipynb : tokenisation des textes
    - 05_lemmatisation.ipynb : lemmatisation des textes
    - 06_limite_max : limite minimale de longueur pour les textes
- application : contient les scripts d'entrainement et de test des différents modèles de classifiaction automatique
    - 01_division_donnees.ipynb : division des données en corpus de dev et de test
    - 02_dev_tok_perso.ipynb : entrainement sur les données tokenisées avec noms des personnages (3 tags : *Fluff, Angst, Hurt/Comfort*)
    - 03_dev_tok_no_perso.ipynb : entrainement sur les données tokenisées sans noms des personnages (3 tags)
    - 04_dev_lemm_perso.ipynb : entrainement sur les données lemmatisées avec noms des personnages (3 tags)
    - 05_dev_lemm_no_perso.ipynb : entrainement sur les données lemmatisées sans noms des personnages (3 tags)
    - 06_test_LinearSVC.ipynb : optimisation et test sur le meilleur modèle (3 tags)
    - 07_classification_5_tags.ipynb : entrainement et test du meilleur modèle sur les 5 tags

#### *recup_txt_pydistinto*
Contient le script qui a permis de récupérer les textes des fanfictions de chaque tag dans des fichiers txt nécessaire pour l'analyse par pydistinto.

#### *pydistinto*
Ce sous-dossier contient tous les scripts, dossiers et fichiers nécessaires à l'analyse via pydistinto.
Il est organisé ainsi:
- dossier pydistinto : copie du git original (https://github.com/Zeta-and-Company/pydistinto)
- dossier corpus_pls : contient tous les fichiers txt contenant les textes des fanfictions des différents tags. Il est utilisé pour l'analyse en comparaison d'un tag contre les quatre autres.
- dossier corpus : contient deux fichiers txt. Il est utilisé pour l'analyse en comparaison de deux tags en un contre un
- dossier data : à ignorer
- fichier metadata.csv : fichier metadata pour les comparaisons en un contre un
- fichier metadata_pls.csv : fichier metadata pour les comparaisons un contre quatre 
- fichier stoplist.txt : fichier contenant les *stop-words* à prendre en compte lors des prétraitements de pydistinto (vide)

### graphes_pydistinto
Ce dossier contient tous les graphes issus des comparaisons réalisées à l'aide de pydistinto.

Ils sont rangés dans plusieurs sous-dossiers :
- un sous-dossier "all" à l'intérieur duquel se trouvent plusieurs sous-dossiers correspondant aux comparaisons un contre quatre de chaque tag sous la forme "nom_abrégé_du_tag_vs_all".
- des sous-dossiers correspondant aux comparaisons un contre un sous la forme "nom_abrégé_du_tag1_vs_nom_abrégé_du_tag2".

import csv
import logging
import asyncio
from asyncio import Semaphore

import random
from datetime import datetime, timedelta
from typing import List, Dict
from tqdm import tqdm
import aiofiles
import json
from os import environ
from playwright.async_api import async_playwright, Playwright, expect, TimeoutError as PlaywrightTimeoutError

# Les paramètres pour la lecture des profils dans le fichier de données
CSV_FILE = "C:/Users/magueye.gueye/PycharmProjects/Webscraping_AUTO/data/df_profils_sample_2.csv"
START_LINE = 100
END_LINE = 103


TIMEOUT = 2 * 60000
SBR_WS_CDP = 'wss://brd-customer-hl_e9a5f52e-zone-scraping_browser1:jpuci55coo47@brd.superproxy.io:9222'
TARGET_URL = environ.get('TARGET_URL', default='https://www.assurland.com/')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def process_marital_status_and_spouse_info(row: Dict[str, str]) -> Dict[str, str]:
    """
    Processes marital status and adds spouse-related information if applicable.
    """
    marital_statuses_with_spouse = ["Marié(e)", "Concubin(e) / vie maritale", "Pacsé(e)"]

    if row.get('PrimaryApplicantMaritalStatus') in marital_statuses_with_spouse:
        # Generate spouse birth date (as before)
        primary_birth_date = datetime.strptime(row['PrimaryApplicantBirthDate'], '%d/%m/%Y')
        age_difference = random.randint(-1 * 365, 1 * 365)
        spouse_birth_date = primary_birth_date + timedelta(days=age_difference)

        today = datetime.now()
        min_birth_date = today - timedelta(days=18 * 365)
        if spouse_birth_date > min_birth_date:
            spouse_birth_date = min_birth_date - timedelta(days=random.randint(0, 365))

        row['ConjointNonSouscripteurBirthDate'] = spouse_birth_date.strftime('%d/%m/%Y')

        # Add ConjointNonSouscripteurHasDriveLicense
        row['ConjointNonSouscripteurHasDriveLicense'] = random.choice(['Oui', 'Non'])

        # Add ConjointNonSouscripteurDriveLicenseDate if applicable
        if row['ConjointNonSouscripteurHasDriveLicense'] == 'Oui':
            # Generate a random date between spouse's 18th birthday and today
            min_license_date = spouse_birth_date + timedelta(days=18 * 365)
            max_license_date = min(today, spouse_birth_date + timedelta(days=60 * 365))  # Max 60 years after birth

            license_date = min_license_date + timedelta(
                days=random.randint(0, (max_license_date - min_license_date).days))
            row['ConjointNonSouscripteurDriveLicenseDate'] = license_date.strftime('%m/%Y')

    return row

def read_csv_profiles() -> List[Dict[str, str]]:
    encodings = ['ISO-8859-1', 'cp1252', 'latin1']

    for encoding in encodings:
        try:
            with open(CSV_FILE, newline='', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',')
                profiles = []
                for row in list(reader)[START_LINE - 1:END_LINE]:
                    row['CarSelectMode'] = '2'
                    current_datetime = datetime.now()
                    row['DateScraping'] = current_datetime.strftime("%d/%m/%Y")
                    processed_row = process_marital_status_and_spouse_info(row)
                    profiles.append(processed_row)
                    #profiles.append(row)

            logger.info(f"Fichier CSV lu avec succès. Encodage : {encoding}")
            logger.info(f"Nombre de profils lus : {len(profiles)}")

            if profiles:
                logger.info(f"Premier profil : {profiles[0]}")

            return profiles

        except (UnicodeDecodeError, csv.Error) as e:
            logger.error(f"Échec de lecture du fichier CSV avec l'encodage {encoding}: {e}")

    logger.error("Impossible de lire le fichier CSV avec les encodages essayés.")
    return []


def display_profiles(profiles: List[Dict[str, str]], num_lines: int = 5):
    """
    Affiche les premières lignes des profils.

    Args:
        :param profiles: Liste des profils à afficher.
        :param num_lines: Nombre de lignes à afficher (par défaut 5).
    """
    logger.info(f"Affichage des {num_lines} premiers profils :")
    for i, profile in enumerate(profiles[:num_lines], start=1):
        logger.info(f"Profil {i}:")
        for key, value in profile.items():
            logger.info(f"  {key}: {value}")
        logger.info("-" * 50)  # Séparateur entre les profils


async def exponential_backoff(page, url, max_retries=5, initial_timeout=30000):
    for attempt in range(max_retries):
        try:
            timeout = initial_timeout * (2 ** attempt)
            await page.goto(url, timeout=timeout)
            return
        except PlaywrightTimeoutError:
            if attempt < max_retries - 1:
                wait_time = random.uniform(1, 2 ** attempt)
                logger.warning(
                    f"Timeout lors de la navigation vers {url}. Attente de {wait_time:.2f} secondes avant la prochaine tentative.")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Échec de la navigation vers {url} après {max_retries} tentatives")
                raise




""" Pour le remplissage de la premiére page """

async def fill_form_projet(page, profile):

    """
    Remplit le formulaire sur le projet.

    """
    try:
        # Attendre que le formulaire soit chargé
        await page.wait_for_selector('div.al_label span:text("Votre projet")')
        print("Vous avez accés à la page du formulaire 'PROJET' ")
        print(f"Le profil '{profile['Id']}' est lancé....")
        await page.wait_for_selector('.InsuranceNeed', state='visible', timeout=TIMEOUT)
        if profile['InsuranceNeed'] == "Vous comptez l'acheter":
            await page.click('button.list-group-item[value="0"]')
            print(f"----> La valeur '{profile['InsuranceNeed']}' a été choisie...")
            try:
                await page.wait_for_selector('.InsuranceNeedDetail', state='visible', timeout=TIMEOUT)
                print("Le div InsuranceNeedDetail est apparu")
                if profile['InsuranceNeedDetail'] == "D'une voiture en remplacement":
                    await page.click('.InsuranceNeedDetail button.list-group-item[value="2"]')
                    print(f"----> La valeur '{profile['InsuranceNeedDetail']}' a été choisie...")
                elif profile['InsuranceNeedDetail'] == "D'une voiture supplémentaire":
                    await page.click('.InsuranceNeedDetail button.list-group-item[value="3"]')
                    print(f"----> La valeur '{profile['InsuranceNeedDetail']}' a été choisie...")
                elif profile['InsuranceNeedDetail'] == "D'une première voiture":
                    await page.click('.InsuranceNeedDetail button.list-group-item[value="4"]')
                    print(f"----> La valeur '{profile['InsuranceNeedDetail']}' a été choisie...")
                else:
                    print(f"Type d'achat de voiture non reconnu : {profile['InsuranceNeedDetail']}")

                if profile['AddCarAge'] == "Neuve":
                    await page.click('.AddCarAge button.list-group-item[value="1"]')
                    print(f"----> La valeur '{profile['AddCarAge']}' a été choisie...")
                elif profile['AddCarAge'] == "D'occasion":
                    await page.click('.AddCarAge button.list-group-item[value="2"]')
                    print(f"----> La valeur '{profile['AddCarAge']}' a été choisie...")
                else:
                    print(f"Type de détail de voiture non reconnu : {profile['AddCarAge']}")
            except PlaywrightTimeoutError:
                print("Le div InsuranceNeedDetail n'est pas apparu comme prévu")

        elif profile['InsuranceNeed'] == "Vous le possédez déjà":
            await page.click('button.list-group-item[value="1"]')
            print(f"----> La valeur '{profile['InsuranceNeed']}' a été choisie...")
        else:
            print(f"Statut d'achat non reconnu : {profile['InsuranceNeed']}")

        await page.wait_for_selector('.OtherDriver', state='visible', timeout=TIMEOUT)

        if profile['OtherDriver'] == "Oui":
            await page.click('.OtherDriver button.list-group-item[value="3"]')
            print(f"----> La valeur '{profile['OtherDriver']}' a été choisie sur la déclaration d'un conducteur secondaire.")
            try:
                if 'OtherDriverType' in profile:
                    await page.wait_for_selector('#OtherDriverType', state="visible", timeout=TIMEOUT)
                    if profile['OtherDriverType'] == "Votre conjoint ou concubin":
                        await page.select_option('#OtherDriverType', value="1")
                        print(
                            f"----> La valeur '{profile['OtherDriverType']}' a été choisie pour le type du conducteur secondaire.")
                    elif profile['OtherDriverType'] == "Votre enfant":
                        await page.select_option('#OtherDriverType', value="2")
                        print(
                            f"----> La valeur '{profile['OtherDriverType']}' a été choisie pour le type du conducteur secondaire.")
                    elif profile['OtherDriverType'] == "Votre père ou votre mère":
                        await page.select_option('#OtherDriverType', value="3")
                        print(
                            f"----> La valeur '{profile['OtherDriverType']}' a été choisie pour le type du conducteur secondaire.")
                    elif profile['OtherDriverType'] == "Le père ou la mère de votre conjoint ou concubin":
                        await page.select_option('#OtherDriverType', value="4")
                        print(
                            f"----> La valeur '{profile['OtherDriverType']}' a été choisie pour le type du conducteur secondaire.")
                    else:
                        print("Type du conducteur secondaire non reconnu")
                else:
                    print("Type du conducteur secondaire non spécifié dans profile")
            except PlaywrightTimeoutError:
                print("Le div OtherDriverType n'est pas apparu comme prévu")

        elif profile['OtherDriver'] == "Non":
            await page.click('.OtherDriver button.list-group-item[value="1"]')
            print(f"----> La valeur '{profile['OtherDriver']}' a été choisie sur la déclaration d'un conducteur secondaire.")
        else:
            print(f"Déclaration d'un conducteur secondaire : {profile['OtherDriver']}")

        # Titulaire de la carte grise
        if 'GreyCardOwner' in profile:
            await page.wait_for_selector('#GreyCardOwner', state="visible", timeout=TIMEOUT)
            if profile['GreyCardOwner'] == "Vous":
                await page.select_option('#GreyCardOwner', value="1")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            elif profile['OtherDriverType'] == "Votre conjoint ou concubin":
                await page.select_option('#GreyCardOwner', value="2")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            elif profile['OtherDriverType'] == "Vous ET votre conjoint ou concubin":
                await page.select_option('#GreyCardOwner', value="3")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            elif profile['OtherDriverType'] == "Votre père ou votre mère":
                await page.select_option('#GreyCardOwner', value="4")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            elif profile['OtherDriverType'] == "Le père ou la mère de votre conjoint ou concubin":
                await page.select_option('#GreyCardOwner', value="5")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            elif profile['OtherDriverType'] == "Il s'agit d'un véhicule de société":
                await page.select_option('#GreyCardOwner', value="6")
                print(
                    f"----> La valeur '{profile['GreyCardOwner']}' a été choisie pour le Titulaire de la carte grise.")
            else:
                print("Type du Titulaire de la carte grise non reconnu")
        else:
            print("Type du Titulaire de la carte grise non spécifié dans profile")

        print("Toutes les étapes de fill_form_projet ont été complétées avec succès.")

        await asyncio.sleep(2)
        await page.get_by_role("button", name="SUIVANT ").click()
        print("Navigation vers la page suivante : Votre profil.")

    except Exception as e:
        print(f"Une erreur s'est produite lors du remplissage du formulaire PROJET : {str(e)}")


""" Remplissage de la page PROFIL """
async def fill_form_profil(page, profile):
    """
        Remplit le formulaire sur le profil.
    """
    try:
        await page.wait_for_selector('div.al_label span:text("Votre profil")')
        await page.wait_for_selector('.PrimaryApplicantSex', state="visible", timeout=TIMEOUT)
        if profile['PrimaryApplicantSex'] == "Un homme":
            await page.click('.PrimaryApplicantSex button.list-group-item[value="H"]')
            print(f"----> La valeur '{profile['PrimaryApplicantSex']}' a été choisie pour le genre.")
        elif profile['PrimaryApplicantSex'] == "Une femme":
            await page.click('.PrimaryApplicantSex button.list-group-item[value="F"]')
            print(f"----> La valeur '{profile['PrimaryApplicantSex']}' a été choisie pour le genre.")
        else:
            print("Genre non reconnu dans profile")

        await page.wait_for_selector("#PrimaryApplicantBirthDate", state="visible", timeout=60000)
        await page.evaluate('document.getElementById("PrimaryApplicantBirthDate").value = ""')
        await page.fill("#PrimaryApplicantBirthDate", profile['PrimaryApplicantBirthDate'])
        await page.press("#PrimaryApplicantBirthDate", "Enter")
        await page.wait_for_timeout(500)
        entered_value = await page.evaluate('document.getElementById("PrimaryApplicantBirthDate").value')
        if entered_value != profile['PrimaryApplicantBirthDate']:
            raise ValueError(
                f"La date de naissance saisie ({entered_value}) ne correspond pas à la valeur attendue ({profile['PrimaryApplicantBirthDate']})")
        print(f"----> Date de naissance '{profile['PrimaryApplicantBirthDate']}' saisie avec succès.")

        """ Statut matrimonial du profil """
        try:
            await page.wait_for_selector("#PrimaryApplicantMaritalStatus", state="visible", timeout=60000)
            await page.select_option("#PrimaryApplicantMaritalStatus", label=profile['PrimaryApplicantMaritalStatus'])
            print(f"----> Statut marital '{profile['PrimaryApplicantMaritalStatus']}' sélectionné avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la sélection du statut marital: {str(e)}")
            # await page.screenshot(path="error_marital_status.png")
            raise ValueError(f"Erreur lors de la sélection du statut marital : {str(e)}")

        """ Situation prof du profil """
        try:
            await page.wait_for_selector("#PrimaryApplicantOccupationCode", state="visible", timeout=60000)
            await page.select_option("#PrimaryApplicantOccupationCode", label=profile['PrimaryApplicantOccupationCode'])
            print(f"----> Statut professionnel '{profile['PrimaryApplicantOccupationCode']}' sélectionné avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la sélection du statut professionnel: {str(e)}")
            # await page.screenshot(path="error_professional_status.png")
            raise ValueError(f"Erreur lors de la sélection du statut professionnel : {str(e)}")

        """ Date d'obtention du permis du profil """
        try:
            await page.wait_for_selector("#PrimaryApplicantDrivLicenseDate", state="visible", timeout=60000)
            await page.evaluate('document.getElementById("PrimaryApplicantDrivLicenseDate").value = ""')
            await page.fill("#PrimaryApplicantDrivLicenseDate", profile['PrimaryApplicantDrivLicenseDate'])
            await page.press("#PrimaryApplicantDrivLicenseDate", "Enter")
            await page.wait_for_timeout(500)
            print(
                f"----> Date d'obtention du permis '{profile['PrimaryApplicantDrivLicenseDate']}' saisie avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la saisie de la date d'obtention du permis: {str(e)}")
            # await page.screenshot(path="error_driving_license_date.png")
            raise ValueError(f"Erreur lors de la saisie de la date d'obtention du permis : {str(e)}")

        """ Conduite accompagnée pour le profil """
        try:
            await page.wait_for_selector(".PrimaryApplicantIsPreLicenseExper", state="visible", timeout=TIMEOUT)
            buttons = await page.query_selector_all(".PrimaryApplicantIsPreLicenseExper button")
            if not buttons:
                raise ValueError("Les boutons de conduite accompagnée n'ont pas été trouvés.")
            if profile['PrimaryApplicantIsPreLicenseExper'] == "Oui":
                await page.click('.PrimaryApplicantIsPreLicenseExper button.list-group-item[value="True"]')
                print(
                    f"----> La valeur '{profile['PrimaryApplicantIsPreLicenseExper']}' a été choisie pour la conduite accompagnée.")
            elif profile['PrimaryApplicantIsPreLicenseExper'] == "Non":
                await page.click('.PrimaryApplicantIsPreLicenseExper button.list-group-item[value="False"]')
                print(
                    f"----> La valeur '{profile['PrimaryApplicantIsPreLicenseExper']}' a été choisie pour la conduite accompagnée.")
            else:
                raise ValueError(
                    f"Valeur non reconnue pour la conduite accompagnée : {profile['PrimaryApplicantIsPreLicenseExper']}")
        except Exception as e:
            logging.error(f"Erreur lors de la sélection de l'option de conduite accompagnée: {str(e)}")
            # await page.screenshot(path="error_accompanied_driving.png")
            raise ValueError(f"Erreur lors de la sélection de l'option de conduite accompagnée : {str(e)}")

        """ Suspension du permis pour le profil """
        try:
            await page.wait_for_selector("#PrimaryApplicantDrivLicenseSusp", state="visible", timeout=10000)
            await page.select_option("#PrimaryApplicantDrivLicenseSusp",
                                     label=profile['PrimaryApplicantDrivLicenseSusp'])
            selected_value = await page.evaluate('document.getElementById("PrimaryApplicantDrivLicenseSusp").value')
            selected_text = await page.evaluate(
                'document.getElementById("PrimaryApplicantDrivLicenseSusp").options[document.getElementById("PrimaryApplicantDrivLicenseSusp").selectedIndex].text')
            if selected_text != profile['PrimaryApplicantDrivLicenseSusp']:
                raise ValueError(
                    f"Le statut sélectionné ({selected_text}) ne correspond pas au statut attendu ({profile['PrimaryApplicantDrivLicenseSusp']})")
            print(
                f"----> Statut de suspension du permis '{profile['PrimaryApplicantDrivLicenseSusp']}' sélectionné avec succès (valeur: {selected_value}).")
        except Exception as e:
            logging.error(f"Erreur lors de la sélection du statut de suspension du permis: {str(e)}")
            # await page.screenshot(path="error_license_suspension_status.png")
            raise ValueError(f"Erreur lors de la sélection du statut de suspension du permis : {str(e)}")

        """ Votre conjoint ou concubin """
        valid_marital_statuses = ["Marié(e)", "Concubin(e) / vie maritale", "Pacsé(e)"]
        if profile.get('PrimaryApplicantMaritalStatus') in valid_marital_statuses:
            logging.info(f"Le statut marital '{profile.get('PrimaryApplicantMaritalStatus')}' nécessite de remplir l'information sur le permis du conjoint.")
            try:
                await page.wait_for_selector("#ConjointNonSouscripteurBirthDate", state="visible", timeout=60000)
                await page.evaluate('document.getElementById("ConjointNonSouscripteurBirthDate").value = ""')
                await page.fill("#ConjointNonSouscripteurBirthDate", profile['ConjointNonSouscripteurBirthDate'])
                await page.press("#ConjointNonSouscripteurBirthDate", "Enter")
                await page.wait_for_timeout(500)
                print(f"----> Date de naissance '{profile['ConjointNonSouscripteurBirthDate']}' saisie avec succès.")
            except Exception as e:
                logging.error(f"Erreur lors de la saisie de la date de naissance: {str(e)}")
                # await page.screenshot(path="error_birth_date.png")
                raise ValueError(f"Erreur lors de la saisie de la date de naissance : {str(e)}")

            try:
                await page.wait_for_selector('.ConjointNonSouscripteurHasDriveLicense', state='visible', timeout=TIMEOUT)
                if profile['ConjointNonSouscripteurHasDriveLicense'] == "Non":
                    await page.click('.ConjointNonSouscripteurHasDriveLicense button.list-group-item[value="False"]')
                    print(f"----> La valeur '{profile['ConjointNonSouscripteurHasDriveLicense']}' a été choisie pour le conjoint avec un permis.")
                elif profile['ConjointNonSouscripteurHasDriveLicense'] == "Oui":
                    await page.click('.ConjointNonSouscripteurHasDriveLicense button.list-group-item[value="True"]')
                    print(f"----> La valeur '{profile['ConjointNonSouscripteurHasDriveLicense']}' a été choisie pour le conjoint avec un permis.")
                    await page.wait_for_selector("#ConjointNonSouscripteurDriveLicenseDate", state="visible",
                                                 timeout=60000)
                    await page.evaluate('document.getElementById("ConjointNonSouscripteurDriveLicenseDate").value = ""')
                    await page.fill("#ConjointNonSouscripteurDriveLicenseDate", profile['ConjointNonSouscripteurDriveLicenseDate'])
                    await page.press("#ConjointNonSouscripteurDriveLicenseDate", "Enter")
                    await page.wait_for_timeout(500)  # Attendre que le calendrier se ferme
                    print(f"Date d'obtention du permis du conjoint '{profile['ConjointNonSouscripteurDriveLicenseDate']}' saisie avec succès.")
                else:
                    print('Valeur non reconnu pour le permis du conjoint ou concubin')
            except Exception as e:
                print(f"Une erreur soulevé sur les informations du conjoint : {str(e)}")
        else:
            print(f"Le statut marital '{profile.get('PrimaryApplicantMaritalStatus')}' ne nécessite pas de remplir l'information sur le permis du conjoint.")

        """ Vos enfants """
        try:
            await page.wait_for_selector('.HasChild', state='visible', timeout=TIMEOUT)
            if profile['HasChild'] == "Oui":
                await page.click('.HasChild button.list-group-item[value="True"]')
                await page.select_option('#ChildBirthDateYear1', value=profile['ChildBirthDateYear1'])
                print(
                    f"Année de l'enfant 1 '{profile['ChildBirthDateYear1']}' saisie avec succès.")
                await page.select_option('#ChildBirthDateYear2', value=profile['ChildBirthDateYear2'])
                print(
                    f"Année de l'enfant 2'{profile['ChildBirthDateYear2']}' saisie avec succès.")
                await page.select_option('#ChildBirthDateYear3', value=profile['ChildBirthDateYear3'])
                print(
                    f"Année de l'enfant 3 '{profile['ChildBirthDateYear3']}' saisie avec succès.")
            elif profile['HasChild'] == "Non":
                await page.click('.HasChild button.list-group-item[value="False"]')
            else:
                print("Valeur non connue pour les enfants")

        except Exception as e:
            print(f"Une erreur soulevé sur les informations des années de naissance des enfants : {str(e)}")

        await asyncio.sleep(2)
        await page.get_by_role("button", name="SUIVANT ").click()
        print("Navigation vers la page suivante : Votre profil.")
    except Exception as e:
        print(f"Une erreur s'est produite lors du remplissage du formulaire PROFIL : {str(e)}")

""" Pour le remplissage des informations sur les véhicules """

async def fill_form_vehicule(page, profile):
    """

    :param page:
    :param profile:
    :return:
    """
    try:
        await page.wait_for_selector('div.form-group.has-feedback.CarSelectMode', state='visible', timeout=6000)
        if profile['CarSelectMode'] == "1":
            selectmode = await page.wait_for_selector('div.list-group > button.list-group-item[value="1"]')
            await selectmode.click()
            print(
                f"----> L'option avec la valeur '\033[34m{profile['CarSelectMode']}\033[0m' a été sélectionnée avec succès pour la question : la selection de Modéle / Marque. ")
        elif profile['CarSelectMode'] == "2":
            selectmode = await page.wait_for_selector('div.list-group > button.list-group-item[value="2"]')
            await selectmode.click()
            print(
                f"----> L'option avec la valeur '\033[34m{profile['CarSelectMode']}\033[0m' a été sélectionnée avec succès pour la question : la selection de Modéle / Marque. ")
        else:
            raise ValueError("Erreur sur la valeur prise par CarSelectMode")
    except PlaywrightTimeoutError:
        print("Le bouton '.CarSelectMode' n'est pas visible.")
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur les informations de la selection de Modéle / Marque : {str(e)}")

    """ Date d'achat prévue de la voiture """
    try:
        await page.wait_for_selector('#PurchaseDatePrev', state='visible', timeout=6000)
        await page.get_by_label("Date d'achat prévue du vé").click()
        await page.get_by_role("cell", name="Aujourd'hui").click()
        print(
            f"----> L'option avec la valeur Aujourd'hui a été sélectionnée avec succès pour la question : La date d'achat.")
    except PlaywrightTimeoutError:
        print("Le bouton '.PurchaseDatePrev' n'est pas visible.")
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur les informations de la date d'achat prévue : {str(e)}")

    """ Date d'achat de la voiture """
    try:
        await page.wait_for_selector('#PurchaseDate', state='visible', timeout=6000)
        select_PurchaseDate = profile['PurchaseDate']
        await page.type('#PurchaseDate', select_PurchaseDate, strict=True)
        await page.get_by_label("Date d'achat :").click()
        print(
            f"----> L'option avec la valeur '\033[34m{select_PurchaseDate}\033[0m' a été sélectionnée avec succès pour la question : Date d'achat du véhicule. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.PurchaseDate' n'est pas visible.")
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur les informations de la date d'achat : {str(e)}")

    """ Date de mise en circulation """
    try:
        await page.wait_for_selector('#FirstCarDrivingDate', state='visible', timeout=6000)
        await page.type("#FirstCarDrivingDate", profile['FirstCarDrivingDate_2'], strict=True)
        await page.get_by_label("Date de 1ère mise en").click()
        await page.get_by_label("Date de 1ère mise en").press("Enter")
        print(
            f"----> L'option avec la valeur '\033[34m{profile['FirstCarDrivingDate_2']}\033[0m' a été sélectionnée avec succès pour la question : Date de mise en circulation du véhicule. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.FirstCarDrivingDate' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de la date de mise en circulation du véhicule : {str(e)}")

    """ Marque de la voiture """
    try:
        await page.wait_for_selector("#SpecCarMakeName", state="visible", timeout=TIMEOUT)
        await page.select_option("#SpecCarMakeName", label=profile['SpecCarMakeName'])
        print(f"----> Marque de la voiture '{profile['SpecCarMakeName']}' sélectionné avec succès.")
    except PlaywrightTimeoutError:
        print("Le bouton '.SpecCarMakeName' n'est pas visible.")
    except Exception as e:
        logging.error(f"Erreur lors de la sélection de la marque de voiture: {str(e)}")
        raise ValueError(f"Erreur lors de la sélection de la marque de voiture : {str(e)}")

    """ Modéle de la marque de voiture """
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector("#SpecCarType", state="visible", timeout=2 * 60000)
        element_SpecCarType = await page.query_selector("#SpecCarType")
        await element_SpecCarType.wait_for_element_state("enabled", timeout=6000)
        await page.select_option("#SpecCarType", label=profile['SpecCarType'], timeout=6000)
        print(f"----> Modéle de la voiture '{profile['SpecCarType']}' sélectionné avec succès.")
    except PlaywrightTimeoutError:
        print("Le bouton '.SpecCarType' n'est pas visible.")
    except Exception as e:
        logging.error(f"Erreur lors de la sélection du modéle de voiture: {str(e)}")
        raise ValueError(f"Erreur lors de la sélection du modéle de voiture : {str(e)}")

    """ Type d'alimentation de la voiture """
    await asyncio.sleep(3)
    try:
        await page.wait_for_selector("#SpecCarFuelType", state="visible", timeout=TIMEOUT)
        element_SpecCarFuelType = await page.query_selector("#SpecCarFuelType")
        await element_SpecCarFuelType.wait_for_element_state("enabled", timeout=60000)
        await page.select_option("#SpecCarFuelType", value=profile['SpecCarFuelType'], timeout=6000)
        print(f"----> Alimentation de la voiture '{profile['SpecCarFuelType']}' sélectionné avec succès.")
    except PlaywrightTimeoutError:
        print("Le bouton '.SpecCarFuelType' n'est pas visible.")
    except Exception as e:
        logging.error(f"Erreur lors de la sélection de Alimentation de voiture: {str(e)}")
        raise ValueError(f"Erreur lors de la sélection de Alimentation de voiture : {str(e)}")

    """ Type de carrosserie de la voiture """
    await asyncio.sleep(3)
    try:
        await page.wait_for_selector("#SpecCarBodyType", state="visible", timeout=TIMEOUT)
        element_SpecCarBodyType = await page.query_selector("#SpecCarBodyType")
        await element_SpecCarBodyType.wait_for_element_state("enabled", timeout=60000)
        await page.select_option("#SpecCarBodyType", value=profile['SpecCarBodyType'], timeout=6000)
        print(f"----> Carosserie de la voiture '{profile['SpecCarBodyType']}' sélectionnée avec succès.")
    except PlaywrightTimeoutError:
        print(f"Le sélecteur SpecCarBodyType n'est pas devenu visible dans le délai imparti.")
    except Exception as e:
        logging.error(f"Erreur lors de la sélection de la carrosserie de la voiture: {str(e)}")
        raise ValueError(f"Erreur lors de la sélection de la carrosserie de voiture : {str(e)}")

    """ Puissance de la voiture """
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector("#SpecCarPower", state="visible", timeout=TIMEOUT)
        await page.select_option("#SpecCarPower", value=profile['SpecCarPower'], strict=True)
        print(f"----> Puissance de la voiture '{profile['SpecCarPower']}' sélectionnée avec succès.")
    except PlaywrightTimeoutError:
        print(f"Le sélecteur #SpecCarPower n'est pas visible.")
    except Exception as e:
        logging.error(f"Erreur lors de la sélection de la puissance de la voiture: {str(e)}")
        raise ValueError(f"Erreur lors de la sélection de la puissance de voiture : {str(e)}")

    """ ID de la voiture """
    try:
        await page.wait_for_selector('.modal-content', state='visible', timeout=60000)
        select_vehicule = profile['code_vehicule_apsad']
        await page.click(f'#{select_vehicule}')
        print(
            f"----> L'option avec la valeur '\033[34m{select_vehicule}\033[0m' a été sélectionnée avec succès pour la question : ID du véhicule ")
    except PlaywrightTimeoutError:
        print("Le div '.modal-content' n'est pas visible.")
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur les informations de l'ID du véhicule : {str(e)}")



async def run_for_profile(playwright: Playwright, profile: dict, headless: bool, bright_data: bool, url=TARGET_URL) -> None:
    """
    Exécute le script de scraping pour un profil donné.
    """
    await asyncio.sleep(random.uniform(1, 2))
    if bright_data:
        browser = await playwright.chromium.connect_over_cdp(SBR_WS_CDP)
    else:
        browser = await playwright.chromium.launch(headless=headless, slow_mo=3)
    context = await browser.new_context()
    # Créer une nouvelle page
    page = await context.new_page()


    await asyncio.sleep(2)

    try:
        # Dans votre fonction run_for_profile :
        await exponential_backoff(page, 'https://www.assurland.com/')
        actions = [
            page.get_by_role("button", name="Continuer sans accepter").click,
            page.get_by_role("button", name="Tout accepter").click
        ]
        await random.choice(actions)()
        AUTO_INSURANCE_SELECTOR = "div.al_product.al_car[title='Comparez les assurances auto']"
        await page.wait_for_selector(AUTO_INSURANCE_SELECTOR, state="visible", timeout=30000)
        auto_insurance_div = page.locator(AUTO_INSURANCE_SELECTOR)
        await expect(auto_insurance_div).to_be_enabled(timeout=30000)
        await auto_insurance_div.click()
        logger.info("Cliqué sur le div 'Comparez les assurances auto'")
        print(f"Le profil '{profile['Id']}' est lancé....")

        await fill_form_projet(page, profile)
        await page.wait_for_load_state("networkidle")
        logger.info("=" * 100)
        await fill_form_profil(page, profile)
        logger.info("=" * 100)
        await fill_form_vehicule(page, profile)
        logger.info("=" * 100)


    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du profil: {str(e)}")
        await page.screenshot(path="error_run_for_profile.png")
        raise
    finally:
        await context.close()
        await browser.close()


async def main(headless: bool, bright_data: bool, max_concurrent: int = 1):
    profiles = read_csv_profiles()
    if not profiles:
        logger.error("Aucun profil n'a été lu. Fin du programme.")
        return
    semaphore = Semaphore(max_concurrent)
    progress_bar = tqdm(total=len(profiles), desc="Traitement des profils")

    display_profiles(profiles)

    async with async_playwright() as playwright:
        tasks = [
            run_for_profile_with_semaphore_and_progress(playwright, profile, headless, bright_data, semaphore,
                                                        progress_bar)
            for profile in profiles
        ]
        await asyncio.gather(*tasks)

    progress_bar.close()




# Fonction wrapper pour utiliser le sémaphore
async def run_for_profile_with_semaphore_and_progress(playwright, profile, headless, bright_data, semaphore,
                                                      progress_bar):
    async with semaphore:
        try:
            await run_for_profile(playwright, profile, headless, bright_data)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du profil {profile['Id']}: {str(e)}")
        finally:
            progress_bar.update(1)


if __name__ == "__main__":
    asyncio.run(main(headless=False, bright_data=False, max_concurrent=1))

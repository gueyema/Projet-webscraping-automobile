import csv
import logging
import asyncio
from asyncio import Semaphore
import datetime

import random
from datetime import datetime, timedelta
from typing import List, Dict
from tqdm import tqdm
import aiofiles
import json
from os import environ
from playwright.async_api import async_playwright, Playwright, expect, TimeoutError as PlaywrightTimeoutError

# Les paramètres pour la lecture des profils dans le fichier de données
CSV_FILE = "C:/Users/User/Documents/GitHub/Projet-webscraping-automobile/data/df_profils_v1.csv"
START_LINE = 201
END_LINE = 1000


TIMEOUT = 2 * 60000
SBR_WS_CDP = 'wss://brd-customer-hl_e9a5f52e-zone-scraping_browser1:jpuci55coo47@brd.superproxy.io:9222'
TARGET_URL = environ.get('TARGET_URL', default='https://www.assurland.com/')

# Liste d'agents utilisateurs
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/113.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/127.0.2651.105",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/113.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Xbox; Xbox One) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edge/44.18363.8131",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"]

# Liste de langues
LANGUAGES = ["fr-FR", "en-GB", "de-DE", "es-ES"]

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
                    row['FreqCarUse'] = '1'
                    row['ContractAnniverMth'] = row['ContractAnniverMth'].zfill(2)
                    row['Phone'] = row['Phone'].zfill(10)
                    row['JobParkZipCode'] = row['JobParkZipCode'].zfill(5)
                    row['JobParkInseeCode'] = row['JobParkInseeCode'].zfill(5)
                    row['HomeParkZipCode'] = row['HomeParkZipCode'].zfill(5)
                    row['HomeParkInseeCode'] = row['HomeParkInseeCode'].zfill(5)
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

    """ Condition si le projet consiste à un achat de véhicule neuf """
    try:
        if profile['InsuranceNeed'] == "Vous comptez l'acheter" and profile['AddCarAge'] == "Neuve":
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

            """ Marque de la voiture """
            try:
                await page.wait_for_selector("#SpecCarMakeName", state="visible", timeout=TIMEOUT)
                await page.select_option("#SpecCarMakeName", label=profile['car_make_value'])
                print(f"----> Marque de la voiture '{profile['car_make_value']}' sélectionné avec succès.")
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
                await page.select_option("#SpecCarType", label=profile['car_type_value'], timeout=6000)
                print(f"----> Modéle de la voiture '{profile['car_type_value']}' sélectionné avec succès.")
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
                await page.select_option("#SpecCarFuelType", value=profile['alimentation_value'], timeout=6000)
                print(f"----> Alimentation de la voiture '{profile['alimentation_value']}' sélectionné avec succès.")
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
                await page.select_option("#SpecCarBodyType", value=profile['carosserie_value'], timeout=6000)
                print(f"----> Carosserie de la voiture '{profile['carosserie_value']}' sélectionnée avec succès.")
            except PlaywrightTimeoutError:
                print(f"Le sélecteur SpecCarBodyType n'est pas devenu visible dans le délai imparti.")
            except Exception as e:
                logging.error(f"Erreur lors de la sélection de la carrosserie de la voiture: {str(e)}")
                raise ValueError(f"Erreur lors de la sélection de la carrosserie de voiture : {str(e)}")

            """ Puissance de la voiture """
            await asyncio.sleep(2)
            try:
                await page.wait_for_selector("#SpecCarPower", state="visible", timeout=TIMEOUT)
                await page.select_option("#SpecCarPower", value=profile['puissance_value'], strict=True)
                print(f"----> Puissance de la voiture '{profile['puissance_value']}' sélectionnée avec succès.")
            except PlaywrightTimeoutError:
                print(f"Le sélecteur #SpecCarPower n'est pas visible.")
            except Exception as e:
                logging.error(f"Erreur lors de la sélection de la puissance de la voiture: {str(e)}")
                raise ValueError(f"Erreur lors de la sélection de la puissance de voiture : {str(e)}")

            """ ID de la voiture """
            try:
                await page.wait_for_selector('.modal-content', state='visible', timeout=60000)
                select_vehicule = profile['id']
                await page.click(f'#{select_vehicule}')
                print(
                    f"----> L'option avec la valeur '\033[34m{select_vehicule}\033[0m' a été sélectionnée avec succès pour la question : ID du véhicule ")
            except PlaywrightTimeoutError:
                print("Le div '.modal-content' n'est pas visible.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations de l'ID du véhicule : {str(e)}")
        else:
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
                await page.type("#FirstCarDrivingDate", profile['FirstCarDrivingDate_1'], strict=True)
                await page.get_by_label("Date de 1ère mise en").click()
                await page.get_by_label("Date de 1ère mise en").press("Enter")
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['FirstCarDrivingDate_1']}\033[0m' a été sélectionnée avec succès pour la question : Date de mise en circulation du véhicule. ")
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
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur les informations de la marque du véhicule : {str(e)}")

    """ Mode de financement """
    try:
        await page.wait_for_selector('#PurchaseMode', state='visible', timeout=60000)
        await page.select_option('#PurchaseMode', value=profile['PurchaseMode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['PurchaseMode']}\033[0m' a été sélectionnée avec succès pour la question : Mode de financement. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.PurchaseMode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations du mode de financement {str(e)}")

    """ Usage prévu  """
    try:
        await page.wait_for_selector('#CarUsageCode', state='visible', timeout=60000)
        await page.select_option('#CarUsageCode', value=profile['CarUsageCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['CarUsageCode']}\033[0m' a été sélectionnée avec succès pour la question : Usage prévu . ")
    except PlaywrightTimeoutError:
        print("Le bouton '.CarUsageCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de l'usage prévu {str(e)}")

    """ Kilomètres parcourus par an  """
    try:
        await page.wait_for_selector('#AvgKmNumber', state='visible', timeout=60000)
        await page.select_option('#AvgKmNumber', value=profile['AvgKmNumber'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['AvgKmNumber']}\033[0m' a été sélectionnée avec succès pour la question : Kilomètres parcourus par an. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.AvgKmNumber' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations du Kilomètres parcourus par an {str(e)}")

    """ Combien de fois en moyenne utilisez-vous votre véhicule  """
    try:

        await page.wait_for_selector('#FreqCarUse', state='visible', timeout=30000)
        await page.select_option('#FreqCarUse', value=profile['FreqCarUse'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['FreqCarUse']}\033[0m' a été sélectionnée avec succès pour la question : Combien de fois en moyenne utilisez-vous votre véhicule. ")

    except PlaywrightTimeoutError:
        print("Le bouton '.FreqCarUse' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de la fréquence d'usage {str(e)}")

    """ Code postal du lieu de stationnement la nuit  """
    try:
        await page.wait_for_selector('#HomeParkZipCode', state='visible', timeout=60000)
        await page.type('#HomeParkZipCode', profile['HomeParkZipCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['HomeParkZipCode']}\033[0m' a été sélectionnée avec succès pour la question : Code postal du lieu de stationnement la nuit. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.HomeParkZipCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations du code postal du lieu de stationnement : {str(e)}")

    """ Ville du lieu de stationnement la nuit  """
    try:
        await page.wait_for_selector('#HomeParkInseeCode', state='visible', timeout=60000)
        await page.select_option('#HomeParkInseeCode', value=profile['HomeParkInseeCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['HomeParkInseeCode']}\033[0m' a été sélectionnée avec succès pour la question : Ville du lieu de stationnement la nuit. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.HomeParkInseeCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de la ville du lieu de stationnement : {str(e)}")

    """ Votre résidence principale  """
    try:
        await page.wait_for_selector('#HomeType', state='visible', timeout=60000)
        await page.select_option('#HomeType', value=profile['HomeType'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['HomeType']}\033[0m' a été sélectionnée avec succès pour la question : Votre résidence principale. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.HomeType' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de Votre résidence principale : {str(e)}")

    """ Type de location """
    try:
        await page.wait_for_selector('#HomeResidentType', state='visible', timeout=60000)
        await page.select_option('#HomeResidentType', value=profile['HomeResidentType'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['HomeResidentType']}\033[0m' a été sélectionnée avec succès pour la question : Type de location . ")
    except PlaywrightTimeoutError:
        print("Le bouton '.HomeResidentType' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de Votre Type de location : {str(e)}")

    """ Code postal du lieu de travail  """
    try:
        await page.wait_for_selector('#JobParkZipCode', state='visible', timeout=6000)
        await page.type('#JobParkZipCode', profile['JobParkZipCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['JobParkZipCode']}\033[0m' a été sélectionnée avec succès pour la question : Code postal du lieu de travail. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.JobParkZipCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations du Code postal du lieu de travail : {str(e)}")

    """ Ville du lieu de travail   """
    try:
        await page.wait_for_selector('#JobParkInseeCode', state='visible', timeout=6000)
        await page.select_option('#JobParkInseeCode', value=profile['JobParkInseeCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['JobParkInseeCode']}\033[0m' a été sélectionnée avec succès pour la question : Ville du lieu de travail. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.JobParkInseeCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations de la Ville du lieu de travail : {str(e)}")

    """ Mode de parking la nuit """
    try:
        await page.wait_for_selector('#ParkingCode', state='visible', timeout=60000)
        await page.select_option('#ParkingCode', value=profile['ParkingCode'])
        print(
            f"----> L'option avec la valeur '\033[34m{profile['ParkingCode']}\033[0m' a été sélectionnée avec succès pour la question : Mode de parking la nuit. ")
    except PlaywrightTimeoutError:
        print("Le bouton '.ParkingCode' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur les informations du Mode de parking la nuit : {str(e)}")
    try:
        await asyncio.sleep(2)
        await page.get_by_role("button", name="SUIVANT ").click()
        print("Navigation vers la page suivante : Vos antécédents.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur le click du bouton suivant : {str(e)}")

    """ Les antécédents du profil """

async def fill_antecedents(page, profile):
    try:
        await page.wait_for_selector('.al_label span', state='visible', timeout=6000)
        # Récupérer le texte du span
        title_text = await page.locator('.al_label span').text_content()
        if title_text.strip() == "Vos antécédents":
            try:
                await page.wait_for_selector("select[name='PrimaryApplicantHasBeenInsured']", state='visible', timeout=2 * 60000)
                if profile['PrimaryApplicantHasBeenInsured'] == "N":
                    await page.select_option("#PrimaryApplicantHasBeenInsured", value=profile['PrimaryApplicantHasBeenInsured'])
                    print(f"Option sélectionnée pour la question initiale : {profile['PrimaryApplicantHasBeenInsured']}")
                    print("Réponse 'Non' sélectionnée. Pas d'autres champs à remplir.")
                else:
                    try:
                        await page.wait_for_selector("select[name='PrimaryApplicantHasBeenInsured']", state='visible',
                                                     timeout=2 * 60000)
                        await page.select_option("#PrimaryApplicantHasBeenInsured", value=profile['PrimaryApplicantHasBeenInsured'])
                        await page.wait_for_selector('#PrimaryApplicantInsuranceYearNb', state='visible', timeout=60000)
                        await page.select_option('#PrimaryApplicantInsuranceYearNb', value=profile['PrimaryApplicantInsuranceYearNb'])
                        print(
                            f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantInsuranceYearNb']}\033[0m' a été sélectionnée avec succès pour la question : Assuré sans interruption depuis ?. ")
                    except PlaywrightTimeoutError:
                        print("Le bouton '.PrimaryApplicantInsuranceYearNb' n'est pas visible.")
                    except Exception as e:
                        raise ValueError(
                            f"Erreur d'exception sur les informations des antécédents de l'assuré : {str(e)}")

                    """ Etes-vous désigné conducteur principal d'un autre véhicule et assuré à ce titre ? """
                    try:
                        await page.wait_for_selector('.PrimaryApplicantIsFirstDrivOtherCar', state='visible', timeout=60000)
                        if profile['PrimaryApplicantIsFirstDrivOtherCar'] == "Oui":
                            await page.click('div.PrimaryApplicantIsFirstDrivOtherCar button[value="True"]')
                        elif profile['PrimaryApplicantIsFirstDrivOtherCar'] == "Non":
                            await page.click('div.PrimaryApplicantIsFirstDrivOtherCar button[value="False"]')
                        else:
                            raise ValueError("Erreur sur la valeur prise par PrimaryApplicantIsFirstDrivOtherCar")
                        print(
                            f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantIsFirstDrivOtherCar']}\033[0m' a été sélectionnée avec succès pour la question : Etes-vous désigné conducteur principal d'un autre véhicule et assuré à ce titre ?.")
                    except PlaywrightTimeoutError:
                        print("L'élément '.PrimaryApplicantIsFirstDrivOtherCar' n'est pas visible, passage au champ suivant.")
                    except Exception as e:
                        raise ValueError(f"Erreur d'exception sur les informations des antécédents du conducteur : {str(e)}")

                    """ Avez-vous fait l'objet d'une résiliation par un assureur au cours des 3 dernières années ? """
                    try:
                        await page.wait_for_selector('#PrimaryApplicantContrCancell', state='visible', timeout=60000)
                        await page.select_option('#PrimaryApplicantContrCancell', value=profile['PrimaryApplicantContrCancell'])
                        print(
                            f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantContrCancell']}\033[0m' a été sélectionnée avec succès pour la question : Avez-vous fait l'objet d'une résiliation par un assureur au cours des 3 dernières années ? . ")
                    except PlaywrightTimeoutError:
                        print("Le bouton '.PrimaryApplicantContrCancell' n'est pas visible.")
                    except Exception as e:
                        raise ValueError(
                            f"Erreur d'exception sur les informations des antécédents de l'assuré : {str(e)}")

                    """ Quel est votre bonus-malus auto actuel ? """
                    try:
                        await page.wait_for_selector('#PrimaryApplicantBonusCoeff', state='visible', timeout=60000)
                        await page.select_option('#PrimaryApplicantBonusCoeff', value=profile['PrimaryApplicantBonusCoeff'],
                                                 strict=True)
                        print(
                            f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantBonusCoeff']}\033[0m' a été sélectionnée avec succès pour la question : Quel est votre bonus-malus auto actuel ?. ")
                    except PlaywrightTimeoutError:
                        print("Le bouton '.PrimaryApplicantBonusCoeff' n'est pas visible.")
                    except Exception as e:
                        raise ValueError(
                            f"Erreur d'exception sur les informations des antécédents de l'assuré : {str(e)}")

                    """ Combien de sinistres avez-vous déclaré (y compris bris de glace) ? """
                    try:
                        await page.wait_for_selector('#PrimaryApplicantDisasterLast3year', state='visible', timeout=60000)
                        await page.select_option('#PrimaryApplicantDisasterLast3year',
                                                 value=profile['PrimaryApplicantDisasterLast3year'])
                        print(
                            f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantDisasterLast3year']}\033[0m' a été sélectionnée avec succès pour la question : Combien de sinistres avez-vous déclaré (y compris bris de glace) ? . ")
                    except PlaywrightTimeoutError:
                        print("Le bouton '.PrimaryApplicantDisasterLast3year' n'est pas visible.")
                    except Exception as e:
                        raise ValueError(
                            f"Erreur d'exception sur les informations des antécédents de l'assuré : {str(e)}")
            except PlaywrightTimeoutError:
                print("Le bouton '.PrimaryApplicantHasBeenInsured' n'est pas visible.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations des antécédents de l'assuré : {str(e)}")
            try:
                await asyncio.sleep(2)
                await page.get_by_role("button", name="SUIVANT ").click()
                print("Navigation vers la page suivante : Votre contrat.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur le click du bouton suivant : {str(e)}")
        else:
            print(f"Le titre trouvé est '{title_text}', ce qui ne correspond pas à 'Vos antécédents'.")

    except PlaywrightTimeoutError:
        print("Le bouton '..al_label span' n'est pas visible.")
    except Exception as e:
        raise ValueError(
            f"Erreur d'exception sur l'affichage de la page des antécédents: {str(e)}")

async def fill_form_contrats(page, profile):
    try:
        await page.wait_for_selector('.al_label span', state='visible', timeout=60000)
        title_text = await page.locator('.al_label span').text_content()
        if title_text.strip() == "Votre contrat":
            try:
                await page.wait_for_selector('#PrimaryApplicantHomeAddressType', state='visible', timeout=6000)
                await page.select_option('#PrimaryApplicantHomeAddressType',
                                         value=profile['PrimaryApplicantHomeAddressType'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['PrimaryApplicantHomeAddressType']}\033[0m' a été sélectionnée avec succès pour la question : Où résidez-vous ?.")
            except PlaywrightTimeoutError:
                print("Le bouton '.PrimaryApplicantHomeAddressType' n'est pas visible.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat de l'assuré : {str(e)}")

            """ Depuis combien d'années possédez-vous votre véhicule ? """
            try:
                await page.wait_for_selector('#CarOwningTime', state='visible', timeout=6000)
                await page.select_option('#CarOwningTime', value=profile['CarOwningTime'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['CarOwningTime']}\033[0m' a été sélectionnée avec succès pour la question : Depuis combien d'années possédez-vous votre véhicule ?. ")
            except PlaywrightTimeoutError:
                print("Le bouton '.CarOwningTime' n'est pas visible.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat de l'assuré : {str(e)}")

            """ Comment votre véhicule actuel est-il assuré ? """
            try:
                await page.wait_for_selector('.CurrentGuaranteeCode', state='visible', timeout=6000)
                if profile['CurrentGuaranteeCode'] == "A":
                    await page.click('div.CurrentGuaranteeCode button[value="A"]')
                elif profile['CurrentGuaranteeCode'] == "E":
                    await page.click('div.CurrentGuaranteeCode button[value="E"]')
                elif profile['CurrentGuaranteeCode'] == "N":
                    await page.click('div.CurrentGuaranteeCode button[value="N"]')
                else:
                    raise ValueError("Erreur sur la valeur prise par CurrentGuaranteeCode")
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['CurrentGuaranteeCode']}\033[0m' a été sélectionnée avec succès pour la question : Comment votre véhicule actuel est-il assuré ?.")
            except PlaywrightTimeoutError:
                print("L'élément '.CurrentGuaranteeCode' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations du contrat : {str(e)}")

            """ Quel est votre dernier assureur auto ? """
            try:
                await page.wait_for_selector('#CurrentCarrier', state='visible', timeout=6000)
                await page.select_option('#CurrentCarrier', value=profile['CurrentCarrier'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['CurrentCarrier']}\033[0m' a été sélectionnée avec succès pour la question : Quel est votre dernier assureur auto ?. ")
            except PlaywrightTimeoutError:
                print("Le bouton '.CurrentCarrier' n'est pas visible.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations du contrat : {str(e)}")

            """ Quel est le mois d'échéance de votre contrat actuel ? """
            try:
                await page.wait_for_selector('#ContractAnniverMth', state='visible', timeout=6000)
                await page.wait_for_selector('#ContractAnniverMth', state='attached', timeout=10000)
                await page.select_option('#ContractAnniverMth', value=profile['ContractAnniverMth'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['ContractAnniverMth']}\033[0m' a été sélectionnée avec succès pour la question : Quel est le mois d'échéance de votre contrat actuel ?. ")
            except PlaywrightTimeoutError:
                print("Le bouton '.ContractAnniverMth' n'est pas visible.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations du contrat : {str(e)}")

            """ A quelle date souhaitez-vous que votre nouveau contrat débute ? """
            try:
                await page.wait_for_selector('#EffectiveDate', state='visible', timeout=6000)
                await page.locator(".input-group-addon > .fal").click()
                await page.get_by_role("cell", name="Aujourd'hui").click()
                print(
                    f"----> L'option avec la valeur 'Aujourd'hui' a été sélectionnée avec succès pour la question : A quelle date souhaitez-vous que votre nouveau contrat débute ?.")
            except PlaywrightTimeoutError:
                print("Le bouton '.EffectiveDate' n'est pas visible.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            """ Quel niveau de protection voulez-vous ? """
            try:
                await page.wait_for_selector('.ContrGuaranteeCode', state='visible', timeout=600)
                if profile['ContrGuaranteeCode'] == "A":
                    await page.click('div.ContrGuaranteeCode button.list-group-item[value="A"]')
                elif profile['ContrGuaranteeCode'] == "E":
                    await page.click('div.ContrGuaranteeCode button.list-group-item[value="E"]')
                elif profile['ContrGuaranteeCode'] == "C":
                    await page.click('div.ContrGuaranteeCode button.list-group-item[value="C"]')
                elif profile['ContrGuaranteeCode'] == "D":
                    await page.click('div.ContrGuaranteeCode button.list-group-item[value="D"]')
                else:
                    raise ValueError("Erreur sur la valeur prise par ContrGuaranteeCode")
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['ContrGuaranteeCode']}\033[0m' a été sélectionnée avec succès pour la question : Quel niveau de protection voulez-vous ?.")
            except PlaywrightTimeoutError:
                print("L'élément '.ContrGuaranteeCode' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('.UserOptIn', state='visible', timeout=6000)
                if profile['UserOptIn'] == '1':
                    await page.click('div.UserOptIn button.list-group-item[value="1"]')
                else:
                    await page.click('div.UserOptIn button.list-group-item[value="0"]')
            except PlaywrightTimeoutError:
                print("Le bouton '.UserOptIn' n'est pas visible.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur l'acceptation de recevoir des offres : {str(e)}")

            try:
                """ Les coordonnées de l'assuré """
                await page.wait_for_selector('#TitleAddress', state='visible', timeout=6000)
                if profile['TitleAddress'] == 'MONSIEUR':
                    await page.select_option('#TitleAddress', value="MONSIEUR")
                elif profile['TitleAddress'] == 'MADAME':
                    await page.select_option('#TitleAddress', value="MADAME")
                else:
                    raise ValueError("Erreur sur la valeur prise par TitleAddress ")
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['TitleAddress']}\033[0m' a été sélectionnée avec succès pour la civilité ")
            except PlaywrightTimeoutError:
                print("L'élément '.TitleAddress' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(
                    f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('#LastName', state='visible', timeout=6000)
                await page.type('#LastName', profile['LastName'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['LastName']}\033[0m' a été sélectionnée avec succès pour le Nom.")
            except PlaywrightTimeoutError:
                print("L'élément '.LastName' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('#FirstName', state='visible', timeout=6000)
                await page.type('#FirstName', profile['FirstName'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['FirstName']}\033[0m' a été sélectionnée avec succès pour le Prénom.")
            except PlaywrightTimeoutError:
                print("L'élément '.FirstName' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('#Address', state='visible', timeout=6000)
                await page.type('#Address', profile['Address'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['Address']}\033[0m' a été sélectionnée avec succès pour l'adresse.")
            except PlaywrightTimeoutError:
                print("L'élément '.Address' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('#ZipCode', state='visible', timeout=6000)
                for char in profile['HomeParkZipCode']:
                    await page.type('#ZipCode', char)
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['HomeParkZipCode']}\033[0m' a été sélectionnée avec succès pour le Code Postal.")
            except PlaywrightTimeoutError:
                print("L'élément '.ZipCode' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('input#Email', state='visible', timeout=6000)
                for char in profile['Email']:
                    await page.type('input#Email', char)
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['Email']}\033[0m' a été sélectionnée avec succès pour le Mail.")
            except PlaywrightTimeoutError:
                print("L'élément '.Email' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('input#Phone', state='visible', timeout=6000)
                await page.fill('input#Phone', profile['Phone'])
                print(
                    f"----> L'option avec la valeur '\033[34m{profile['Phone']}\033[0m' a été sélectionnée avec succès pour le Téléphone")
            except PlaywrightTimeoutError:
                print("L'élément '.Phone' n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception sur les informations du contrat : {str(e)}")

            try:
                await page.wait_for_selector('.col-xs-12.no-gutter.text-center', state='visible', timeout=6000)
                if profile['Id'] != '0000':
                    await page.click('text="Oui, je la conserve"')
                else:
                    await page.click('text="Non, je la modifie"')
                print("==> Choix effectué avec succès.")
            except PlaywrightTimeoutError:
                print("Les boutons ne sont pas visibles, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception : {str(e)}")
                # Attendre que la case à cocher soit visible
            await page.wait_for_selector('#LegalCGU', state='visible', timeout=6000)
            # Cocher la case en cliquant dessus
            await page.check('#LegalCGU')
            print(f"'\033[34m ==> Case LegalCGU cochée avec succès.\033[0m")

            try:
                # Attendre que la case à cocher soit visible
                await page.wait_for_selector('#LegalRGPD', state='visible', timeout=6000)
                # Cocher la case en cliquant dessus
                await page.check('#LegalRGPD')
                print(f"'\033[34m ==> Case LegalRGPD cochée avec succès.\033[0m")
            except PlaywrightTimeoutError:
                print("La case à cocher n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception : {str(e)}")

            try:
                # Attendre que la case à cocher soit visible
                await page.wait_for_selector('#LegalPartner', state='visible', timeout=6000)
                # Cocher la case
                await page.check('#LegalPartner')
                print(f"'\033[34m ==> Case LegalPartner cochée avec succès. \033[0m")

                await page.get_by_label("J'accepte les conditions géné").check()
                print(f"'\033[34m ===> J'accepte les condions générales \033[0m")
                await page.get_by_label(
                    "Je reconnais avoir reçu les informations relatives à la collecte, le traitement").check()
                print(
                    f"'\033[34m ===> Je reconnais voir reçu les informations relatives à la collecte, le traitement \033[0m")
                await page.get_by_label("J'accepte d'être contacté au").check()
                print(f"'\033[34m ===> J'accepte d'être contacté \033[0m")
            except PlaywrightTimeoutError:
                print("La case à cocher n'est pas visible, passage au champ suivant.")
            except Exception as e:
                raise ValueError(f"Erreur d'exception : {str(e)}")
        else:
            print(f"Le titre trouvé est '{title_text}', ce qui ne correspond pas à 'Vos antécédents'.")
    except Exception as e:
        raise ValueError(f"Erreur lors du remplissage du contrat : {str(e)}")


async def recup_tarifs(page, profile):
    try:
        await asyncio.sleep(random.uniform(1, 3))
        await page.get_by_role("button", name="ACCÉDEZ À VOS DEVIS ").click()

        client = await page.context.new_cdp_session(page)
        print('Waiting captcha to solve...')
        solve_res = await client.send('Captcha.waitForSolve', {
            'detectTimeout': 10000,
        })
        print('Captcha solve status:', solve_res['status'])

        print('Navigated! Scraping page content...')
        print(
            f"'\033[34m ============== ACCÉDEZ À VOS DEVIS pour le profil avec l'identifiant {profile['Id']}....\033[0m")
        await page.wait_for_load_state('load', timeout=60000)
        # Attendre que le formulaire et les offres soient visibles
        await page.wait_for_selector('.al_form .al_content .container-fluid', state='visible', timeout=5 * 60000)

        offres = await page.query_selector_all('.al_content .container-fluid')
        profile_details = []

        for offre in offres:
            element_assureur = await offre.query_selector('.al_carrier')
            assureur = await element_assureur.inner_text()

            element_prime = await offre.query_selector('.al_premium')
            prime = await element_prime.inner_text()

            # Ajouter les détails de l'offre dans la liste
            profile_details.append({

                'Compagnie': assureur,
                'Prime': prime,
                'ID': profile['Id'],
                'TypeBesoin': profile['InsuranceNeed'],
                'TypeBesoinDetails': profile['InsuranceNeedDetail'],
                'AgeCar': profile['AddCarAge'],
                'OtherDriver': profile['OtherDriver'],
                'CarteGrise': profile['GreyCardOwner'],
                'Genre': profile['PrimaryApplicantSex'],
                'DateNaissance': profile['PrimaryApplicantBirthDate'],
                'Age': profile['CalculatedAge'],
                'SituationMatrimoniale': profile['PrimaryApplicantMaritalStatus'],
                'Profession': profile['PrimaryApplicantOccupationCode'],
                'DateObtentionPermis': profile['PrimaryApplicantDrivLicenseDate'],
                'ConduiteAccompagné': profile['PrimaryApplicantIsPreLicenseExper'],
                'DateNaissanceConjoint': profile['ConjointNonSouscripteurBirthDate'],
                'DatePermisConjoint': profile['ConjointNonSouscripteurDriveLicenseDate'],

                'Enfants_a_charge': profile['HasChild'],
                'nbre_enfants': profile['nbre_enfants'],
                'Annee_Enfant_1': profile['ChildBirthDateYear1'],
                'Annee_Enfant_2': profile['ChildBirthDateYear2'],
                'Annee_Enfant_3': profile['ChildBirthDateYear3'],
                'DateAchat': profile['PurchaseDate'],
                'DateAchat_Prevue': profile['PurchaseDatePrev'],
                'DateCirculation': profile['FirstCarDrivingDate_1'],
                'Marque': profile['SpecCarMakeName'],
                'Modele': profile['SpecCarType'],
                'Alimentation': profile['SpecCarFuelType'],
                'Carrosserie': profile['SpecCarBodyType'],
                'Puissance': profile['SpecCarPower'],
                'Marque_vehicule_neuf': profile['car_make_value'],
                'Modele_vehicule_neuf': profile['car_type_value'],
                'Alimentation_vehicule_neuf': profile['alimentation_value'],
                'Carrosserie_vehicule_neuf': profile['carosserie_value'],
                'Puissance_vehicule_neuf': profile['puissance_value'],
                'ID_vehicule_occasion': profile["code_vehicule_apsad"],
                'ID_vehicule_neuf': profile["id"],
                'valeur_a_neuf_vehicule': profile['valeur_a_neuf_vehicule'],
                'groupe_tarification_vehicule': profile['groupe_tarification_vehicule'],
                'classe_tarification_vehicule': profile['classe_tarification_vehicule'],
                'code_type_frequence_rcm': profile['code_type_frequence_rcm'],
                'code_type_frequence_rcc': profile['code_type_frequence_rcc'],
                'code_type_frequence_dta': profile['code_type_frequence_dta'],
                'code_type_frequence_vol': profile['code_type_frequence_vol'],
                'code_type_vol_vehicule': profile['code_type_vol_vehicule'],
                'code_type_frequence_bdg': profile['code_type_frequence_bdg'],
                'ModeFinancement': profile['PurchaseMode'],
                'Usage': profile['CarUsageCode'],
                'KmParcours': profile['AvgKmNumber'],

                'CP_Stationnement': profile['HomeParkZipCode'],
                'Ville_Stationnement': profile['HomeParkInseeCode'],
                'ResidenceType': profile['HomeType'],
                'TypeLocation': profile['HomeResidentType'],
                'CP_Travail': profile['JobParkZipCode'],
                'Ville_Travail': profile['JobParkInseeCode'],
                'nom_commune': profile['nom_commune'],
                'Departement_Code': profile['DepartementCode'],
                'Type_Parking': profile['ParkingCode'],
                'TypeAssure': profile['PrimaryApplicantHasBeenInsured'],
                'NbreAnneeAssure': profile['PrimaryApplicantInsuranceYearNb'],

                'Bonus': profile['PrimaryApplicantBonusCoeff'],

                'NbreAnneePossessionVeh': profile['CarOwningTime'],
                'CtrActuel': profile['CurrentGuaranteeCode'],
                'AssureurActuel': profile['CurrentCarrier'],
                'NiveauProtection': profile['ContrGuaranteeCode'],
                'Date_scraping': profile['DateScraping']
            })
        if profile_details:
            date_du_jour = datetime.now().strftime("%d_%m_%y")
            nom_fichier_json = f"offres_assureurs_auto_v2_{date_du_jour}.json"
            # Écrire les offres dans le fichier JSON
            async with aiofiles.open(nom_fichier_json, mode='a') as f:
                await f.write(json.dumps(profile_details))
                await f.write('\n')
                print(f"=====> Les offres du profil {profile['Id']} ont été stockées dans le fichier:",
                      nom_fichier_json)
        else:

            date_du_jour = datetime.now().strftime("%d_%m_%y")
            nom_fichier_sans_tarif = f"fichiers_profils_sans_{date_du_jour}.json"
            # Écrire les informations du profil dans le fichier JSON des échecs
            async with aiofiles.open(nom_fichier_sans_tarif, mode='a') as f:
                await f.write(json.dumps({'ID': profile['Id']}))
                await f.write('\n')
                print(f"=====> Le profil {profile['Id']} a été stocké dans le fichier des échecs:", nom_fichier_sans_tarif)

    except PlaywrightTimeoutError:
        print("Le div '.al_form' n'est pas visible, passage au champ suivant.")
    except Exception as e:
        raise ValueError(f"Erreur d'exception sur la recupération des offres : {str(e)}")


async def get_random_browser(playwright: Playwright, bright_data: bool, headless: bool):
    browser_choice = random.choice(['chromium', 'firefox'])
    slow_mo = random.randint(500, 800)
    viewport = {
      "width": random.randint(1024, 1920),
      "height": random.randint(768, 1080)
    }
    user_agent = random.choice(USER_AGENTS)
    language = random.choice(LANGUAGES)

    launch_options = {
      "headless": headless,
      "slow_mo": slow_mo,
    }

    if bright_data:
        browser = await playwright.chromium.connect_over_cdp(SBR_WS_CDP)
    else:
        browser = await getattr(playwright, browser_choice).launch(**launch_options)

    context = await browser.new_context(
      viewport=viewport
    )

    logger.info(f"{browser_choice.capitalize()} a été choisi avec les options : {launch_options}, viewport: {viewport}, user_agent: {user_agent}, locale: {language}")
    return browser, context

async def simulate_human_behavior(page):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight * Math.random());")
    await page.wait_for_timeout(random.randint(1000, 3000))
    await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
    await page.wait_for_timeout(random.randint(500, 1500))


async def run_for_profile(playwright: Playwright, profile: dict, headless: bool, bright_data: bool,
                          url=TARGET_URL) -> None:
    await asyncio.sleep(random.uniform(1, 2))

    await asyncio.sleep(random.uniform(1, 2))

    browser, context = await get_random_browser(playwright, bright_data, headless)
    page = await context.new_page()

    # Ajouter un script furtif
    await page.add_init_script("""
          Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
          Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});""")

    try:
        await exponential_backoff(page, url)
        await simulate_human_behavior(page)

        actions = [
            page.get_by_role("button", name="Continuer sans accepter").click,
            page.get_by_role("button", name="Tout accepter").click
        ]
        await random.choice(actions)()
        await simulate_human_behavior(page)

        AUTO_INSURANCE_SELECTOR = "div.al_product.al_car[title='Comparez les assurances auto']"
        await page.wait_for_selector(AUTO_INSURANCE_SELECTOR, state="visible", timeout=30000)
        auto_insurance_div = page.locator(AUTO_INSURANCE_SELECTOR)
        await expect(auto_insurance_div).to_be_enabled(timeout=30000)
        await auto_insurance_div.click()
        await simulate_human_behavior(page)

        logger.info("Cliqué sur le div 'Comparez les assurances auto'")
        print(f"Le profil '{profile['Id']}' est lancé....")

        await fill_form_projet(page, profile)
        #await simulate_human_behavior(page)
        await page.wait_for_load_state("networkidle")
        logger.info("=" * 100)
        await fill_form_profil(page, profile)
        #await simulate_human_behavior(page)
        await page.wait_for_load_state("networkidle")
        logger.info("=" * 100)
        await fill_form_vehicule(page, profile)
        #await simulate_human_behavior(page)
        await page.wait_for_load_state("networkidle")
        logger.info("=" * 100)
        await fill_antecedents(page, profile)
        #await simulate_human_behavior(page)
        await page.wait_for_load_state("networkidle")
        logger.info("=" * 100)
        await fill_form_contrats(page, profile)
        #await simulate_human_behavior(page)
        logger.info("=" * 100)
        await recup_tarifs(page, profile)






    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du profil: {str(e)}")
        date_du_jour = datetime.now().strftime("%d_%m_%y")

        # Créer le nom du fichier avec la date du jour
        nom_fichier_echecs = f"fichiers_profils_echecs_{date_du_jour}.json"
        # Écrire les informations du profil dans le fichier JSON des échecs
        async with aiofiles.open(nom_fichier_echecs, mode='a') as f:
            await f.write(json.dumps({'ID': profile['Id']}))
            await f.write('\n')
            print(f"=====> Le profil {profile['Id']} a été stocké dans le fichier des échecs:", nom_fichier_echecs)
        raise
    finally:
        await context.close()
        await browser.close()






async def main(headless: bool, bright_data: bool, max_concurrent: int = 20):
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
    asyncio.run(main(headless=False, bright_data=True, max_concurrent=20))

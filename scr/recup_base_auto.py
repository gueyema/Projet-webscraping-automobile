from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Any
import asyncio
from random import random
import random
from datetime import datetime, timedelta
import time
import csv
import json
import aiofiles

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Page,
    ElementHandle,
)


start_year = 2000
end_year = 2024

marques = ["RENAULT", "AUDI", "CITROEN","PEUGEOT", "BMW", "DACIA"]

async def parse_modal_content(page: Page) -> Dict[str, Any]:
    modal = await page.query_selector(".modal-content")
    if not modal:
        return {}

    # Extract title
    title = await modal.query_selector(".modal-title")
    title_text = await title.inner_text() if title else ""

    # Extract vehicle info
    vehicle_info = await modal.query_selector(".modal-body .modal-title")
    vehicle_info_text = await vehicle_info.inner_text() if vehicle_info else ""

    # Extract filter options
    version_filter = await modal.query_selector("#SearchGtaCode")
    version_filter_placeholder = await version_filter.get_attribute("placeholder") if version_filter else ""

    # Extract gearbox options
    gearbox_options = await modal.query_selector_all("#SearchGearBoxLabel option")
    gearbox_options_text = [await option.inner_text() for option in gearbox_options]

    # Extract doors options
    doors_options = await modal.query_selector_all("#SearchDoorsNumber option")
    doors_options_text = [await option.inner_text() for option in doors_options]

    # Extract vehicles
    vehicles = await modal.query_selector_all(".list-group-item")
    vehicle_list = []
    for vehicle in vehicles:

        vehicle_id = await vehicle.get_attribute("id")
        vehicle_name = await vehicle.query_selector("strong")
        vehicle_name_text = await vehicle_name.inner_text() if vehicle_name else ""
        vehicle_year = await vehicle.query_selector(".col-sm-3")
        vehicle_year_text = await vehicle_year.inner_text() if vehicle_year else ""
        vehicle_details = await vehicle.query_selector(".col-xs-12.small")
        vehicle_details_text = await vehicle_details.inner_text() if vehicle_details else ""

        vehicle_list.append({
          "id": vehicle_id,
          "name": vehicle_name_text,
          "year": vehicle_year_text,
          "details": vehicle_details_text
        })

        return {"vehicles": vehicle_list}

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, slow_mo=1500)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto('https://www.assurland.com/', timeout=2 * 60 * 1000)


            actions = [
                page.get_by_role("button", name="Continuer sans accepter").click,
                page.get_by_role("button", name="Tout accepter").click
            ]
            await random.choice(actions)()
            await page.get_by_title("Comparez les assurances auto").click()

            print("Visite de l'onglet pour les devis Auto")
            print("=" * 100)
            print("============== Début de scrapping ....")
            print("=" * 100)
            await page.get_by_role("button", name="Vous comptez l'acheter").click()
            await page.get_by_role("button", name="Neuve").click()

            await page.get_by_role("button", name="Non").click()
            await page.get_by_label("Qui est le titulaire de la").select_option("1")
            await page.get_by_role("button", name="SUIVANT ").click()
            await page.get_by_label("Votre date de naissance :").click()
            await page.get_by_role("table").get_by_text("1980", exact=True).click()
            await page.get_by_label("Votre date de naissance :").dblclick()
            await page.get_by_label("Votre date de naissance :").click()
            await page.get_by_text("févr.").click()
            await page.get_by_role("cell", name="30").click()
            await page.get_by_label("Votre situation matrimoniale :").select_option("N")
            await page.get_by_role("button", name="Oui").first.click()
            await page.get_by_label("La date de naissance de votre").click()
            await page.get_by_role("table").get_by_text("1980", exact=True).click()
            await page.get_by_label("La date de naissance de votre").dblclick()

            await page.get_by_text("janv.").click()
            await page.get_by_role("cell", name="1", exact=True).first.click()
            await page.get_by_role("button", name="SUIVANT ").click()

            await page.get_by_placeholder("Saisissez votre date").click()
            await page.get_by_role("cell", name="3").first.click()
            await asyncio.sleep(5)
            select_car_make = await page.query_selector('#SpecCarMakeName')
            car_make_options = await select_car_make.query_selector_all('option')

            for car_make_option in car_make_options:
                car_make_value = await car_make_option.get_attribute("value")
                marque = ["LEXUS", "MAZDA", "SKODA", "VOLKSWAGEN", "VOLVO"]
                if car_make_value in marque:
                    try:
                        await select_car_make.select_option(value=str(car_make_value), timeout=60000)
                        print(f"La marque {car_make_value} a été choisie pour l'année ")
                    except Exception as e:
                        print(f"Erreur lors de la sélection de la marque {car_make_value}: {e}")
                        continue

                    # Attendre que la liste des modèles soit visible
                    await page.wait_for_selector('#SpecCarType', state='visible', timeout=60000)

                    # Récupérer l'élément de la liste déroulante des modèles
                    select_car_type = await page.query_selector('#SpecCarType')
                    car_type_options = await select_car_type.query_selector_all('option')
                    # Parcourir et sélectionner chaque modèle
                    for car_type_option in car_type_options:
                        car_type_value = await car_type_option.get_attribute("value")

                        if car_type_value:
                            try:
                                # Sélectionner l'option du modèle
                                await select_car_type.select_option(value=str(car_type_value), timeout=60000)
                                print(f"  Modèle {car_type_value} sélectionné pour la marque {car_make_value}.")
                            except Exception as e:
                                print(f"  Erreur lors de la sélection du modèle {car_type_value}: {e}")
                                continue

                            # Sélectionner le type d'alimentation
                            await page.wait_for_selector('#SpecCarFuelType', state='visible', timeout=6000)
                            select_alimentation = await page.query_selector('#SpecCarFuelType')
                            alimentation_options = await select_alimentation.query_selector_all('option')

                            for alimentation_option in alimentation_options:
                                alimentation_value = await alimentation_option.get_attribute('value')
                                if alimentation_value:
                                    try:
                                        await select_alimentation.select_option(value=str(alimentation_value))
                                        print(
                                            f"------------> Le type d'alimentation {alimentation_value} a été choisi pour la marque {car_make_value} et le modèle {car_type_value}")
                                    except Exception as e:
                                        print(
                                            f"Erreur lors de la sélection du type d'alimentation {alimentation_value}: {e}")
                                        continue
                                    # Sélectionner le type de carrosserie
                                    await page.wait_for_selector('#SpecCarBodyType', state='visible', timeout=6000)
                                    select_carosserie = await page.query_selector('#SpecCarBodyType')
                                    carosserie_options = await select_carosserie.query_selector_all('option')

                                    for carosserie_option in carosserie_options:
                                        carosserie_value = await carosserie_option.get_attribute('value')
                                        if carosserie_value:
                                            try:
                                                await select_carosserie.select_option(
                                                    value=str(carosserie_value), timeout=60000)
                                                print(
                                                    f"-------------------------> Le type de carrosserie {carosserie_value} a été choisi pour le type d'alimentation {alimentation_value}, la marque {car_make_value} et le modèle {car_type_value}")
                                            except Exception as e:
                                                print(
                                                    f"Erreur lors de la sélection du type de carrosserie {carosserie_value}: {e}")
                                                continue
                                            # Sélectionner la puissance
                                            await page.wait_for_selector('#SpecCarPower', state='visible',
                                                                         timeout=6000)
                                            select_spec_car_power = await page.query_selector('#SpecCarPower')
                                            spec_car_power_options = await select_spec_car_power.query_selector_all(
                                                'option')

                                            for spec_car_power_option in spec_car_power_options:
                                                spec_car_power_value = await spec_car_power_option.get_attribute(
                                                    'value')
                                                if spec_car_power_value:
                                                    try:
                                                        await select_spec_car_power.select_option(
                                                            value=str(spec_car_power_value), timeout=60000)
                                                        print(
                                                            f"-----------------------------------------------> La puissance {spec_car_power_value} a été choisie pour le type de carrosserie {carosserie_value}, le type d'alimentation {alimentation_value}, la marque {car_make_value} et le modèle {car_type_value}")
                                                    except Exception as e:
                                                        print(
                                                            f"Erreur lors de la sélection de la puissance {spec_car_power_value}: {e}")
                                                        continue

                                                    await page.wait_for_selector(".modal-content", state="visible",
                                                                                 timeout=10000)
                                                    modal = await page.query_selector(".modal-content")
                                                    vehicles = await modal.query_selector_all(".list-group-item")
                                                    vehicle_list = []
                                                    for vehicle in vehicles:
                                                        vehicle_id = await vehicle.get_attribute("id")
                                                        vehicle_name = await vehicle.query_selector("strong")
                                                        vehicle_name_text = await vehicle_name.inner_text() if vehicle_name else ""
                                                        vehicle_year = await vehicle.query_selector(".col-sm-3")
                                                        vehicle_year_text = await vehicle_year.inner_text() if vehicle_year else ""
                                                        vehicle_details = await vehicle.query_selector(
                                                            ".col-xs-12.small")
                                                        vehicle_details_text = await vehicle_details.inner_text() if vehicle_details else ""

                                                        vehicle_list.append({
                                                            "car_make_value": car_make_value,
                                                            "car_type_value": car_type_value,
                                                            "alimentation_value": alimentation_value,
                                                            "carosserie_value": carosserie_value,
                                                            "puissance_value": spec_car_power_value,
                                                            "id": vehicle_id,
                                                            "name": vehicle_name_text,
                                                            "year": vehicle_year_text,
                                                            "details": vehicle_details_text})

                                                    async with aiofiles.open('base_voitures_SRA.json',
                                                                             mode='a') as f:
                                                        await f.write(json.dumps(vehicle_list) + '\n')
                                                        print(
                                                            f"Informations écrites dans le fichier JSON pour la voiture {car_make_value}, modèle {car_type_value}")









        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
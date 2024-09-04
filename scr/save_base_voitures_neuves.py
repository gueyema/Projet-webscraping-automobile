import json
import re


file_path = r"C:\Users\magueye.gueye\PycharmProjects\Webscraping_AUTO\data\base_voitures_SRA.json"
def clean_and_parse_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Nettoyer le contenu
    content = content.replace('\n', '').replace('\r', '')

    # Trouver tous les objets JSON valides
    pattern = r'\{[^{}]*\}'
    json_objects = re.findall(pattern, content)

    all_data = []
    for json_str in json_objects:
        try:
            obj = json.loads(json_str)
            all_data.append(obj)
        except json.JSONDecodeError as e:
            print(f"Erreur lors du décodage d'un objet JSON: {e}")
            print(f"Objet problématique: {json_str[:100]}...")  # Afficher les 100 premiers caractères

    return all_data



try:
    data = clean_and_parse_json(file_path)
    print(f"Nombre total d'objets chargés: {len(data)}")
    if data:
        print("Premier objet:")
        print(json.dumps(data[0], indent=2))
        print("\nDernier objet:")
        print(json.dumps(data[-1], indent=2))
    else:
        print("Aucun objet JSON valide n'a été trouvé dans le fichier.")
except FileNotFoundError:
    print(f"Le fichier {file_path} n'a pas été trouvé. Vérifiez le chemin du fichier.")
except Exception as e:
    print(f"Une erreur s'est produite: {e}")

# Sauvegarder en CSV
import csv

csv_file_path = "../data/voitures_SRA.csv"
try:
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        if data:

            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

            print(f"Les données ont été sauvegardées dans {csv_file_path}")
        else:
            print("Aucune donnée à sauvegarder en CSV.")
except Exception as e:
    print(f"Erreur lors de la sauvegarde en CSV: {e}")
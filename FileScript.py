import os
import shutil
import subprocess
import csv
import logging
from typing import List, Tuple, Optional


# Konfigurieren des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_group_directories(parent_directory: str) -> List[str]:
    # Gibt eine Liste der Verzeichnisse im übergeordneten Verzeichnis zurück
    try:
        return [dir for dir in os.listdir(parent_directory) if os.path.isdir(os.path.join(parent_directory, dir))]
    except FileNotFoundError:
        logging.error(f"Verzeichnis {parent_directory} nicht gefunden.")
        return []
    
def find_test_directory(project_src_directory: str, group: str) -> Optional[str]:
    # Sucht nach dem Testverzeichnis, das 'test' im Namen enthält, und loggt, wenn es umbenannt wurde <guckt ob es überhaupt test verzeichnise gibt>
    test_directory = None
    for item in os.listdir(project_src_directory):
        if os.path.isdir(os.path.join(project_src_directory, item)) and 'test' in item:
            test_directory = os.path.join(project_src_directory, item)
            if item != 'test':
                logging.warning(f"Testverzeichnis für Gruppe {group} wurde zu '{item}' umbenannt.")
            break
    if test_directory is None:
        logging.error(f"Kein Testverzeichnis für Gruppe {group} gefunden.")
    return test_directory

#konsistenz für die unter ordernamen in den gruppen
def get_subdirectory_name(parent_directory: str, group1: str, group2: str) -> Optional[Tuple[str, str]]:
    group1_path = os.path.join(parent_directory, group1)
    group2_path = os.path.join(parent_directory, group2)

    project_name_1 = project_name_2 = None

    if os.path.isdir(group1_path):
        subdirs = [name for name in os.listdir(group1_path) if os.path.isdir(os.path.join(group1_path, name))]
        if subdirs:
            project_name_1 = subdirs[0]  

    if os.path.isdir(group2_path):
        subdirs = [name for name in os.listdir(group2_path) if os.path.isdir(os.path.join(group2_path, name))]
        if subdirs:
            project_name_2 = subdirs[0]  

    return project_name_1, project_name_2

def swap_and_test(parent_directory: str, group1: str, group2: str) -> Tuple[str, str, int, int]:
    # Führt die Tests mit vertauschten Testverzeichnissen aus und stellt die ursprüngliche Struktur wieder her
    
    runs = success_count = failure_count = errors = skipped = 0

    name1, name2 = get_subdirectory_name(parent_directory, group1, group2)
    # Pfad zum Maven-Projektverzeichnis <pom.xml vorhanden>
    project_dir_1 = os.path.join(parent_directory, group1, name1)
    project_dir_2 = os.path.join(parent_directory, group2, name2)

    # Pfad zum src-Verzeichnis 
    src_dir_1 = os.path.join(parent_directory, group1, name1, 'src')
    src_dir_2 = os.path.join(parent_directory, group2, name2, 'src')

    # Finde die Testverzeichnisse, wenn sie vorhanden sind
    test_dir_1 = find_test_directory(src_dir_1, group1)
    test_dir_2 = find_test_directory(src_dir_2, group2)

    # Wenn ein Testverzeichnis nicht gefunden wurde, logge den Vorfall und überspringe die Gruppe
    if not test_dir_1 or not test_dir_2:
        return group1, group2, 0, 0, 0, 0, 0
    
    backup_dir_1 = test_dir_1 + "_backup"

    try:
        # Sichern und Austauschen der Testordner
        shutil.move(test_dir_1, backup_dir_1)
        shutil.copytree(test_dir_2, test_dir_1, dirs_exist_ok=True)

        logging.info(f"Running Maven in {group1}")

        # Maven-Tests ausführen
        process = subprocess.Popen(["./mvnw", "verify"], cwd=project_dir_1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, error = process.communicate()

        logging.info(f"Running Maven done in {group1}")

        # Output parsen
        runs, success_count, failure_count, errors, skipped = parse_maven_output(output.decode('utf-8').split('\n'))

    except Exception as e:
        logging.error(f"Fehler bei der Ausführung der Tests zwischen {group1} und {group2}: {e}")
        runs, success_count, failure_count, errors, skipped = 0, 0, 0, 0, 0

    finally:
        # Ursprüngliche Ordnerstruktur wiederherstellen
        if os.path.exists(backup_dir_1):
            shutil.rmtree(test_dir_1)
            shutil.move(backup_dir_1, test_dir_1)

    return group1, group2, runs, success_count, failure_count, errors, skipped

def parse_maven_output(output_lines: List[str]) -> Tuple[int, int, int, int, int]:
    runs, failures, errors, skipped = 0, 0, 0, 0
    for line in output_lines:
        if 'Tests run:' in line:
            parts = line.split(',')
            runs = int(parts[0].split(':')[1].strip())
            failures = int(parts[1].split(':')[1].strip())
            errors = int(parts[2].split(':')[1].strip())
            skipped = int(parts[3].split(':')[1].strip())
            success_count = runs - failures - errors - skipped
            failure_count = failures + errors

    return runs, success_count, failure_count, errors, skipped

def write_results_to_csv(results: List[dict], filename: str):
    # Schreibt die Ergebnisse in eine CSV-Datei, erweitert um zusätzliche Felder
    fieldnames = ["Group", "TestedBy", "Runs", "Success", "Failures", "Errors", "Skipped"]
    with open(filename, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {
                "Group": result["Group"],
                "TestedBy": result["TestedBy"],
                "Runs": result["Runs"],
                "Success": result["Success"],
                "Failures": result["Failures"],
                "Errors": result["Errors"],
                "Skipped": result["Skipped"]
            }
            writer.writerow(row)

def main(parent_directory: str):
    results = []
    groups = get_group_directories(parent_directory)
    for i, group1 in enumerate(groups):
        for j, group2 in enumerate(groups):
            if i != j:
                group1, group2, runs, success_count, failure_count, errors, skipped = swap_and_test(parent_directory, group1, group2)
                
                results.append({
                    "Group": group1, 
                    "TestedBy": group2, 
                    "Runs": runs, 
                    "Success": success_count, 
                    "Failures": failure_count, 
                    "Errors": errors, 
                    "Skipped": skipped
                })

    write_results_to_csv(results, 'test_results.csv')

if __name__ == "__main__":
    # Pfad zum übergeordneten Verzeichnis, das die Gruppenordner enthält, beim Testen jeweiliges Directory anpassen hier unten
    parent_directory = r"path/to/parent/directory"
    main(parent_directory)

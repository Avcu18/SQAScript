import os
import subprocess
import csv

results = []

def get_group_directories(parent_directory):
    """Gibt eine Liste der Verzeichnisse im übergeordneten Verzeichnis zurück."""
    return [dir for dir in os.listdir(parent_directory) if os.path.isdir(os.path.join(parent_directory, dir))]

def swap_test_directories(parent_directory):
    groups = get_group_directories(parent_directory)
    for i in range(len(groups)):
        for j in range(len(groups)):
            if i != j:  # Vermeiden Sie, dass eine Gruppe mit sich selbst gepaart wird
                group1 = groups[i]
                group2 = groups[j]

                # Pfade zu den Testordnern und Backup-Ordnern
                test_dir_1 = os.path.join(parent_directory, group1, "test")
                test_dir_2 = os.path.join(parent_directory, group2, "test")
                backup_dir_1 = os.path.join(parent_directory, group1, "test_backup")
                backup_dir_2 = os.path.join(parent_directory, group2, "test_backup")

                # Testordner in Backup umbenennen und austauschen
                os.rename(test_dir_1, backup_dir_1)
                os.rename(test_dir_2, backup_dir_2)
                os.rename(backup_dir_1, test_dir_2)
                os.rename(backup_dir_2, test_dir_1)

                #Subprocess für ausführung von mvn verify, cwd=i damit wir im jeweiligen Ordner sind und standard ausgabe damit wir alle ergebnisse der pipe bekommen
                process = subprocess.Popen(["mvn", "verify"], cwd=i, stdout=subprocess.PIPE)
                output, error = process.communicate()
                
                #ToDO: Output parsen, damit wir success und failure speichern können
                success_count, failure_count = parse_maven_output(output)
                
                #Outputs zusammenfügen, i und j sind die Gruppen die getestet wurden (fyi verwirrung)
                results.append({"Group": i, "TestedBy": j, "Success": success_count, "Failures": failure_count})
                
                # Stellen Sie die ursprüngliche Ordnerstruktur wieder her
                os.rename(test_dir_2, backup_dir_2)
                os.rename(test_dir_1, backup_dir_1)
                os.rename(backup_dir_2, test_dir_2)
                os.rename(backup_dir_1, test_dir_1)

# Ergebnisse in CSV-Datei schreiben
with open('test_results.csv', 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=["Group", "TestedBy", "Success", "Failures"])
    writer.writeheader()
    writer.writerows(results)

#ToDo Parse Maven Output
def parse_maven_output(output):
    success_count = 0
    failure_count = 0
    #Nicht sicher ob das funktioniert, aber grundsätzlich gehen wir zeile für zeile den output durch und suchen nach 'Tests run:', teilen die zeile jeweils immer an den kommas und nehmen dann den zweiten teil der Zeile und berechnen dann success und failure count
    for zeile in output:
        if 'Tests run:' in zeile:
            parts = zeile.split(',')
            runs = int(parts[0].split(':')[1].strip())
            failures = int(parts[1].split(':')[1].strip())
            errors = int(parts[2].split(':')[1].strip())
            skipped = int(parts[3].split(':')[1].strip())
            
            success_count = runs - failures - errors - skipped
            failure_count = failures + errors + skipped
            
    return success_count, failure_count
    
# Pfad zum übergeordneten Verzeichnis, das die Gruppenordner enthält, beim Testen jeweiliges Directory anpassen hier unten
parent_directory = r"C:\Uni\Master\Semester 1\SQA\script\TestProjekte"

swap_test_directories(parent_directory)



import requests
import re
import os
from collections import defaultdict

input_file_name = 'input.txt'
output_file_name = 'output.txt'

current_directory = os.path.dirname(os.path.abspath(__file__))
input_file_path = os.path.join(current_directory, input_file_name)
output_file_path = os.path.join(current_directory, output_file_name)

management_groups = {
    "- - - - - - - - - - - - - - - - - - - - - Центральне управління - - - - - - - - - - - - - - - - - - - - -": ["Винница", "Тульчин", "Жмеринка"],
    "- - - - - - - - - - - - - - - - - - - - - Південне управління - - - - - - - - - - - - - - - - - - - - -": ["Херсон", "Николаев", "Днепр", "Херсон"],
    "- - - - - - - - - - - - - - - - - - - - - Східне управління - - - - - - - - - - - - - - - - - - - - -": ["Полтава", "Кременчуг", "Миргород", "Чернигов", "Харьков"],
    "- - - - - - - - - - - - - - - - - - - - - Західне управління - - - - - - - - - - - - - - - - - - - - -": ["Ровно", "Закарпатье", "Житомир"]
}

cookies = {
    'PHPSESSID': 'сюда свої userside кукі'
}
        
def process_ip(ip):
    url = f'https://userside.homenet.ua/oper/?core_section=homenet_olt&pidr=0&kust=0&city=0&select_city=0&model=0&olt_ip={ip}'
    response = requests.get(url, cookies=cookies)
    
    group_action_pattern = r'id="groupActionId(\d+)"'
    group_action_match = re.search(group_action_pattern, response.text)
    
    if not group_action_match:
        return " "
    
    group_action_id = group_action_match.group(1)
    
    url = f'https://userside.homenet.ua/oper/?core_section=homenet_olt&action=ajax_olt_design_update&oltid={group_action_id}'
    response = requests.get(url, cookies=cookies)
    
    onu_pattern = r'Кількість активних ONU: <span>([0-9-]+)</span>'
    onu_match = re.search(onu_pattern, response.text)
    
    if onu_match:
        final_number = onu_match.group(1)
        if final_number != "-":
            return f" Кількість активних ONU: {final_number}"
        else:
            return " ОЛТ недоступний"

  
def extract_ip_from_line(line):
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    match = re.search(ip_pattern, line)
    if match:
        return match.group(0)
    return None

def format_line(line):
    timestamp_pattern = r'^(?:\d{2}\.\d{2}\.\d{4} )?\d{2}:\d{2}:\d{2}'
    timestamp_match = re.search(timestamp_pattern, line)
    if timestamp_match:
        timestamp = timestamp_match.group(0)
        line = line[len(timestamp_match.group(0)):].strip()  # Remove the timestamp from the beginning
    else:
        return line  # Return the original line if no timestamp is found

    line = re.sub(r'Обновить.*?actions\s*', '', line)
    line = re.sub(r'Обновить.*?действие\s*', '', line)
    line = re.sub(r'Оновити.*?actions\s*', '', line)
    line = re.sub(r'Оновити.?дія\s', '', line)   
    line = line.replace('POWER MONITORING is down', 'на АКБ')
    line = re.sub(r'Interface \d+/\d+\(\): Link down POWER MONITORING', 'на АКБ', line)
    line = re.sub(r'Interface.*?Link down Power Monitoring', 'на АКБ', line)
    line = line.strip()
    line += f' (від {timestamp})'
    
    return line

def extract_pod_fragment(line):
    pod_pattern = r'Под: [^\t\n]+'
    match = re.search(pod_pattern, line)
    if match:
        return match.group(0)
    return None

groups = defaultdict(list)

# Read and group lines
with open(input_file_path, 'r', encoding='utf-8') as infile:
    lines = infile.readlines()
    
    for line in lines:
        ip = extract_ip_from_line(line)
        if ip:
            pod_fragment = extract_pod_fragment(line)
            formatted_line = format_line(line)
            formatted_line = re.sub(r'Под:.*?(?=\(від)', '', formatted_line).strip()
            if pod_fragment:
                groups[pod_fragment].append(formatted_line)
            else:
                groups["No Pod"].append(formatted_line)

# Write grouped and modified lines to the output file
with open(output_file_path, 'w', encoding='utf-8') as outfile:
    total_lines_to_write = sum(len(lines) for lines in groups.values())
    written_lines = 0

    for pod_fragment, lines in groups.items():
        if pod_fragment != "No Pod":
            outfile.write(f"{pod_fragment}\n")
        for line in lines:
            ip = extract_ip_from_line(line)
            if ip:
                result = process_ip(ip)
                if result.endswith('недоступний'):
                    new_line = "❗️ " + line + " " + result + "\n"
                else:
                    new_line = "⚡️ " + line + " " + result + "\n"
            else:
                new_line = line + "\n"
            outfile.write(new_line)
            written_lines += 1

            progress = (written_lines / total_lines_to_write) * 100
            print(f"Progress: {written_lines}/{total_lines_to_write} ({progress:.2f}%)")

def get_management_group(subdivision):
    for group, subdivisions in management_groups.items():
        if subdivision in subdivisions:
            return group
    return "----------------------------------------- Інше управління -----------------------------------------"

def process_file(output_file_path):
    with open(output_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    data = {}
    current_subdivision = None

    # Read and group the data
    for line in lines:
        if line.startswith("Под: "):
            current_subdivision = line.strip()
            if current_subdivision not in data:
                data[current_subdivision] = []
        elif (line.startswith("⚡️") or line.startswith("❗️")) and current_subdivision:
            data[current_subdivision].append(line.strip())

    # Sort and group data by management groups
    grouped_data = {}
    for subdivision, devices in data.items():
        subdivision_name = subdivision.split(": ")[1]
        management_group = get_management_group(subdivision_name)
        if management_group not in grouped_data:
            grouped_data[management_group] = []
        grouped_data[management_group].append((subdivision, devices))

    # Write the sorted data back to the file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        for group, subdivisions in grouped_data.items():
            file.write(group + "\n")
            for subdivision, devices in subdivisions:
                file.write(subdivision + "\n")
                for device in devices:
                    file.write(device + "\n")
                file.write("\n")  # Add an extra newline for readability

process_file(output_file_path)

print(f"Processed lines have been written to {output_file_path}.")

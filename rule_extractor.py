import os
import xml.etree.ElementTree as ET
import csv
from pathlib import Path
from collections import defaultdict

def extract_rules_from_xml(xml_path):
    """Extract all Rule attribute values from an XML file."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Find all elements with Rule attribute
        rules = set()
        for elem in root.iter():
            rule = elem.get('Rule')
            if rule:
                rules.add(rule)
                
        return rules
    except ET.ParseError as e:
        print(f"Error parsing {xml_path}: {str(e)}")
        return set()
    except Exception as e:
        print(f"Unexpected error processing {xml_path}: {str(e)}")
        return set()

def process_xml_directory(directory_path, output_file):
    """Process all XML files in directory and save unique rules to CSV."""
    print(f"Starting to process XML files in {directory_path}")
    
    # Verify directory exists
    if not os.path.exists(directory_path):
        print(f"Error: Directory {directory_path} does not exist")
        return
    
    # Find all XML files recursively
    rule_files = defaultdict(set)  # Dictionary to store rule -> files mapping
    xml_files = list(Path(directory_path).rglob("*.xml"))
    total_files = len(xml_files)
    
    print(f"Found {total_files} XML files to process")
    
    # Process each XML file
    for i, xml_file in enumerate(xml_files, 1):
        print(f"Processing file {i}/{total_files}: {xml_file}")
        file_rules = extract_rules_from_xml(xml_file)
        
        # Add filename to each rule's file list
        filename = xml_file.name
        for rule in file_rules:
            rule_files[rule].add(filename)
    
    # Sort rules alphabetically
    sorted_rules = sorted(rule_files.keys())
    
    # Save to CSV
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Rule', 'Files'])  # Header
            for rule in sorted_rules:
                # Join filenames with commas
                files_str = '|'.join(sorted(rule_files[rule]))
                writer.writerow([rule, files_str])
        
        print(f"\nProcessing complete!")
        print(f"Found {len(sorted_rules)} unique rules")
        print(f"Results saved to {output_file}")
        
    except Exception as e:
        print(f"Error saving CSV file: {str(e)}")

if __name__ == "__main__":
    # Configuration
    # xml_directory = "/home/paulhuang/Documents/IAZH/Rhema-Backend/ReNew-Phrases-OT/Macula-OT/WLC/nodes/"
    xml_directory = "/home/paulhuang/Documents/IAZH/Rhema-Backend/Bijal_s Codes/Phrase Output to Database/Final Code/current_data"
    output_csv = "/home/paulhuang/Documents/IAZH/Rhema-Backend/rules.csv"
    
    process_xml_directory(xml_directory, output_csv) 
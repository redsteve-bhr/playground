# Manifest Generator Script

The Manifest Generator Script is a Python 2.7 script that allows you to automatically generate a customised manifest file for GTConnect.

## Prerequisites

1. Before using the script, ensure that you have Python 2.7.18 installed on your system.

2. Only run this script from within an IT Application repository. The script expects to be able to find:
    - At least one folder within the repo's `build/` folder. (I.e. at least one built app)
    - An app.info in the project root.

## Usage

1. Navigate into the repository's `deploy/` folder and run the script using the following command:
    
    ```bash
    python manifestGenerator.py
    ```
2. Optionally, if using Eclipse, locate the `manifestGenerator.py` script under the `deploy/` folder in the Project Explorer menu. 
    - Right-click the python script > Run As > Python Run

3. The script will generate a manifest file based on the template specific to the current project (`manifestTemplate.json`) and replace the template placeholders with values obtained from app.info.

4. The script will create a ZIP file containing the generated manifest file, an icon image file, and the built .app file. The ZIP file will be named based on the package name and version, e.g., `PackageName-v.1.0.0+GtConnect.zip`.

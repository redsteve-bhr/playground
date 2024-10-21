import os
import json
import zipfile
import re

APP_INFO_PATH               = "../app.info"
ICON_FILE_PATH              = '{}/icon.png'
MANIFEST_TEMPLATE_FILE_PATH = '{}/manifestTemplate.json'
OUTPUT_FOLDER_PATH          = '../build/{}/'
BUILD_FOLDER_PATH           = "../build/"

validityChecks = {
    "name":             r'^.*$',
    "version":          r'^\d+\.\d+.\d+.*',
    "versionCode":      r'^\d+\.\d+.\d+.*',
}


def readAppInfo():
    # Pull data from the build's .info file. Obtains the "version" field.
    try:
        appInfoDict = {}
        with open(APP_INFO_PATH, 'r') as f:
            for line in f:
                key, value = line.strip().split('=', 1)
                appInfoDict[key.strip()] = value.strip().replace("'", "")

        return appInfoDict
    except:
        return None

def getApplicationData():
    # Pull only necessary data from app info and validity check it.
    appInfo = readAppInfo()

    appData = {
        "name":  appInfo["name"],
        "version":  appInfo["version"]
    }

    for field in appData:
        if(not re.match(validityChecks[field], appData[field])):
            print("Error: Bad {} - Value: {}".format(field, appData[field]))
            return -1

    return appData

def injectValueIntoTemplateField(data, field, value):
    data = data.replace("${%s}" % field, value)
    return data

def generateManifest(appData):
    manifestPath = MANIFEST_TEMPLATE_FILE_PATH.format(appData["name"])

    with open(manifestPath, 'r') as json_file:
        manifestData = json_file.read()

    for field in appData:
        manifestData = injectValueIntoTemplateField(manifestData, field, appData[field])
    
    return json.loads(manifestData)

def generateZipName(generatedManifest, projectName):
    major = generatedManifest["version"].split(".")[0]
    minor = generatedManifest["version"].split(".")[1]
    patch = generatedManifest["version"].split(".")[2].split("-")[0]
    return "{}-v.{}.{}.{}+GtConnect.zip".format(projectName, major, minor, patch)

def getTargetBuild(appData):
    buildFolders = [f for f in os.listdir(BUILD_FOLDER_PATH) if os.path.isdir(os.path.join(BUILD_FOLDER_PATH, f))]
    targetBuild = "{}-{}".format(appData["name"], appData["version"])

    if(targetBuild not in buildFolders):
        print("Error: Target build folder not found - Expected: build/{}/".format(targetBuild))
        exit()
    
    return targetBuild

def saveFilesAndZip(appData, generatedManifest):
    with open("manifest.json", 'w') as json_file:
        json.dump(generatedManifest, json_file, indent=4)

    targetBuild = getTargetBuild(appData)
    iconPath = ICON_FILE_PATH.format(appData["name"])
    zipName = generateZipName(generatedManifest, appData["name"])
    zipPath = OUTPUT_FOLDER_PATH.format(targetBuild)

    with zipfile.ZipFile("{}{}".format(zipPath, zipName), 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write("manifest.json", arcname="manifest.json")
        zipf.write(iconPath, arcname="icon.png")
        zipf.write(os.path.join(BUILD_FOLDER_PATH, targetBuild, "{}.app".format(targetBuild)), arcname="{}.app".format(targetBuild))

    os.remove("manifest.json")


if __name__ == "__main__":
    # Get application data from either the script call arguments, or from user inputs. Inject to manifest template, save copy, and zip up.
    appData = getApplicationData()
    if(appData == -1):
        exit()
    
    manifestData = generateManifest(appData)

    saveFilesAndZip(appData, manifestData)
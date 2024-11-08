#! /bin/bash

# The script is a simple bash script that takes a git repo as input, 
# validates it looks like a valid path, and then clones the repo
# to a local directory with the same name as the repo. 
# The script can be run with the following command: 
# ./scan.sh https://github.com/org/repo.git

# Check if the user has provided a git repo as input
if [ -z "$1" ]; then
  echo "Please provide a git repo as input in the format https://github.com/org/repo.git"
  exit 1
fi

# Check if the git repo looks like a valid path
if [[ ! $1 =~ ^https://github.com/.*\.git$ ]]; then
  echo "Please provide a valid github repo in the format https://github.com/org/repo.git"
  exit 1
fi

# Set up variables
export USE_VDB_10Y=true
export FETCH_LICENSE=true
EXEC_DIR=$PWD 
# A GITHUB_TOKEN must exist to download security advisories from GitHub
GIT_CREDS=$GITHUB_TOKEN
# Check if the GITHUB_TOKEN exists
if [ -z "$GIT_CREDS" ]; then
  echo "Please set the GITHUB_TOKEN environment variable"
  exit 1
fi
# Remove https://github.com/ and .git from the git repo path
REPO=$(echo $1 | sed 's|https://github\.com/||' | sed 's|.git$||')
# Get the name of the repo without .git extension
REPO_NAME=$(basename $REPO)
# Set up local directory to clone into
LOCAL_DIR=$PWD/$REPO_NAME

# Shallow clone the git repo to a local directory
echo "--- Cloning https://gitlab.com/$REPO.git"
git clone --depth=1 https://oauth2:$GIT_CREDS@github.com/$REPO.git $LOCAL_DIR

# Check if the clone was successful
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to clone the repo"
  exit 1
fi
echo "---- Successfully cloned https://gitlab.com/$REPO.git"

# Run the sca-scan command on the cloned repo
echo "--- Running sca-scan on $LOCAL_DIR"
cd $LOCAL_DIR
depscan --debug --src $LOCAL_DIR --profile appsec --no-vuln-table --reports-dir $EXEC_DIR/reports --report-name $REPO_NAME

# Once scan is complete, rename and move the generated bom file to the reports directory
echo "--- Moving bom.json to $EXEC_DIR/reports/$REPO_NAME-bom.json\n"
mv bom.json $EXEC_DIR/reports/$REPO_NAME-bom.json

echo "--- sca-scan completed, cleaning up\n\n"
cd $EXEC_DIR
rm -rf $LOCAL_DIR

exit 0
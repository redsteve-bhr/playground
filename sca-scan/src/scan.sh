#! /bin/bash

# The script is a simple bash script that takes a git repo as input, 
# validates it looks like a valid path, and then clones the repo
# to a local directory with the same name as the repo. 
# The script can be run with the following command: 
# ./scan.sh https://github.com/org/repo.git
# Or, to loop through a file:
# while IFS= read -r line; do ./scan.sh $line; done < repo_list.txt

# NOTE: Need to pull vdb (see https://github.com/appthreat/vdb/pkgs/container/vdb) before running scan.

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

# Set up variables for the depscan command
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
echo -e "\n---- SCA SCAN STARTING ----\n"
echo "---- Cloning https://gitlab.com/$REPO.git"
git clone --depth=1 https://oauth2:$GIT_CREDS@github.com/$REPO.git $LOCAL_DIR

# Check if the clone was successful
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to clone the repo"
  exit 1
fi
echo -e "---- Successfully cloned https://gitlab.com/$REPO.git\n"

# generate an SBOM for the repo
echo -e "---- Generating SBOM for $LOCAL_DIR\n"
cd $LOCAL_DIR
cdxgen -r --profile appsec -o $REPO_NAME-bom.json
# TODO Look into using Syft for this

# Once bom generation is complete, rename and move the generated bom file to the reports directory
echo -e "---- Moving $REPO_NAME-bom.json to $EXEC_DIR/reports\n\n"
mv bom.json $EXEC_DIR/reports/$REPO_NAME-bom.json

# perform semgrep scan on the repo
echo -e "---- Running semgrep on $REPO_NAME\n"
semgrep scan --config auto --json-output=/scan/reports/$REPO_NAME-sca.json

# perform grype scan on the repo
echo -e "---- Running grype on $REPO_NAME\n"

echo -e "---- SCA scan completed, cleaning up\n\n"
rm -rf $LOCAL_DIR

exit 0
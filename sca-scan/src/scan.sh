#! /bin/bash

# The script is a simple bash script that takes a git repo as input, 
# validates it looks like a valid path, and then clones the repo
# to a local directory with the same name as the repo. 
# The script can be run with the following command: 
# ./scan.sh https://github.com/org/repo.git
# Or, to loop through a file:
# while IFS= read -r line; do ./scan.sh $line; done < repo_list.txt

# NOTE: Need to pull vdb (see https://github.com/appthreat/vdb/pkgs/container/vdb) before running scan.

# Function to perform scan on a single repository
scan_repo() {
  local repo_url=$1
  # Check if the git repo looks like a valid path
  if [[ ! $repo_url =~ ^https://github.com/.*\.git$ ]]; then
    echo "Invalid GitHub repo: $repo_url"
    return
  fi

  # Remove https://github.com/ and .git from the git repo path
  REPO=$(echo $repo_url | sed 's|https://github\.com/||' | sed 's|.git$||')
  # Get the name of the repo without .git extension
  REPO_NAME=$(basename $REPO)
  # Set up local directory to clone into
  LOCAL_DIR=$PWD/$REPO_NAME

  # Shallow clone the git repo to a local directory
  echo -e "\n---- SCA SCAN STARTING for $REPO_NAME ----\n"
  git clone --depth=1 https://oauth2:$GIT_CREDS@github.com/$REPO.git $LOCAL_DIR

  # Check if the clone was successful
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to clone the repo $REPO_NAME"
    return
  fi

  # generate an SBOM for the repo
  echo -e "---- Generating SBOM for $LOCAL_DIR\n"
  cd $LOCAL_DIR
  cdxgen -r --profile appsec -o /scan/reports/$REPO_NAME-bom.json

  # perform semgrep scan on the repo
  echo -e "---- Running semgrep on $REPO_NAME\n"
  semgrep scan --config auto --json-output=/scan/reports/$REPO_NAME-sca.json

  # perform syft scan on the repo
  echo -e "---- Running syft on $REPO_NAME\n"
  syft -o syft-json=/scan/reports/$REPO_NAME-syft.json --from dir $LOCAL_DIR

  # perform grype scan on the repo
  echo -e "---- Running grype on $REPO_NAME\n"
  grype -o json=/scan/reports/$REPO_NAME-grype.json sbom:/scan/reports/$REPO_NAME-syft.json

  echo -e "---- SCA scan completed for $REPO_NAME, cleaning up\n\n"
  rm -rf $LOCAL_DIR
}

# Main script logic
if [ -z "$1" ]; then
  echo "Please provide a git repo URL or a file containing a list of repos."
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

if [ -f "$1" ]; then
  # If the input is a file, read each line as a repo URL
  while IFS= read -r repo_url; do
    scan_repo "$repo_url"
  done < "$1"
else
  # Otherwise, treat the input as a single repo URL
  scan_repo "$1"
fi

exit 0

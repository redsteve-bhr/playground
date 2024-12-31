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
  local repo=$(echo "$repo_url" | sed 's|https://github\.com/||' | sed 's|.git$||')
  # Get the name of the repo without .git extension
  local repo_name=$(basename "$repo")
  # Set up local directory to clone into
  local local_dir=$PWD/$repo_name

  # Shallow clone the git repo to a local directory
  echo -e "\n---- SCA SCAN STARTING for $repo_name ----\n"
  git clone --depth=1 https://oauth2:"$GIT_CREDS"@github.com/"$repo".git "$local_dir"

  # Check if the clone was successful
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to clone the repo $repo_name"
    return
  fi

  # perform syft scan on the repo
  # echo -e "---- Running syft on $repo_name\n"
  # syft scan -v -o cyclonedx-xml=/output/reports/"$repo_name"-cdx.xml dir:"$local_dir"
  # TODO We can also use syft to generate a SPDX, CycloneDX, or similar file

  # perform grype scan on the repo. Run twice to generate HTML report
  # echo -e "---- Running grype on $repo_name\n"
  # grype -v -o json=/output/reports/"$repo_name"-grype.json dir:"$local_dir"
  # grype -v -o template=/output/reports/"$repo_name"-grype.html -t /usr/local/share/html.tmpl dir:"$local_dir"

  # perform semgrep scan on the repo
  echo -e "---- Running semgrep on $repo_name\n"
  semgrep scan --config auto --sarif --sarif-output=/output/reports/"$repo_name"-sca.sarif

  
  # echo -e "---- Uploading to Dependency Track\n"
  # curl --request POST \
  # --url http://dependency-track-dtrack-apiserver-1:8080/api/v1/bom \
  # --header "X-Api-Key: $DEPTRACK_API_KEY" \
  # --header 'content-type: multipart/form-data' \
  # --form autoCreate=true \
  # --form projectName="$repo_name" \
  # --form projectVersion=2024.11.27 \
  # --form isLatest=true \
  # --form bom=@/output/reports/"$repo_name"-cdx.xml

  echo -e "---- SCA scan completed for $repo_name, cleaning up\n\n"
  rm -rf "$local_dir"
}

# Main script logic
if [ -z "$1" ]; then
  echo "Please provide a git repo URL or a file containing a list of repos."
  exit 1
fi

# A GITHUB_TOKEN must exist to download security advisories from GitHub
GIT_CREDS=$GITHUB_TOKEN
# Check if the GITHUB_TOKEN exists
if [ -z "$GIT_CREDS" ]; then
  echo "Please set the GITHUB_TOKEN environment variable"
  exit 1
fi

if [ -f "$1" ]; then
  # If the input is a file, read each line as a repo URL
  while IFS= read -r url; do
    scan_repo "$url"
  done < "$1"
else
  # Otherwise, treat the input as a single repo URL
  scan_repo "$1"
fi

cp -r /output/reports /scan/reports
# TODO: Look at uploading the data to DependencyTrack or similar

exit 0

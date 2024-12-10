#! /bin/bash
echo "---Stopping and removing existing containers---"
docker stop sca-scanner-dev
docker rm sca-scanner-dev

echo "---Building the dev image---"
docker build -t sca-scanner-dev .

# echo "---Creating reports directory---"
# mkdir reports

echo "---Running the dev image---"
docker run -it \
    -e GITHUB_TOKEN=$GITHUB_PAT \
    -e DEPTRACK_API_KEY=$DEPTRACK_API_KEY \
    -v $(pwd):/scan \
    --network dependency-track_default \
    --name sca-scanner-dev \
    sca-scanner-dev "$1"

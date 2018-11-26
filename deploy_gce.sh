deployment() {
##
# This commend will guide you initialize your gcloud configuration
# Step 0: you will be asked to pick a configuration.
#   Pick configuration to use:
#     [1] Re-initialize this configuration [default] with new settings
#     [2] Create a new configuration
#   $> 1
# Step 1:
#   Choose the account you would like to use to perform operations for
#   this configuration:
#     [1] ******@gmail.com
#     [2] Log in with a new account
#   $> 1
# Step 2:
#   Pick cloud project to use:
#     [1] blablabla
#     [2] Create a new project
#   $> 1
# Step 3:
#   Do you want to configure Google Compute Engine:
#   $> Y
# Step 4:
#   Which Google Compute Engine zone would you like to use as project default?
#     [1] us-east1-b
#     ...
#     [25] asia-east1-b
#     [26] asia-east1-a
#     [27] asia-east1-c
#     ...
#   $> 27
# Step 4:
#   Which Google Compute Engine zone would you like to use as project default?
#     [1] us-east1-b
#     ...
#     [25] asia-east1-b
#     [26] asia-east1-a
#     [27] asia-east1-c
#     ...
#   $> 27
gcloud init

##
# Launch a Google Cloud Engine instance and deploy using a start-script
# 'clevaluate-demo-restful' is the instance's name. change it if needed
##
gcloud compute instances create clevaluate-demo-restful \
--image-family=centos-7 \
--image-project=centos-cloud \
--machine-type=n1-standard-2 \
--scopes userinfo-email,cloud-platform \
--metadata-from-file startup-script=startup-script.sh \
--zone asia-east1-c \
--tags 'http-server'

gcloud compute firewall-rules create default-allow-http-8080 \
--allow tcp:8080 \
--source-ranges 0.0.0.0/0 \
--target-tags http-server \
--description "Allow port 8080 access to http-server"

echo "please run ./check.sh several times until you see following similar result
...
startup-script: [2018-01-25 09:53:27 +0000] [8883] [INFO] Starting gunicorn 19.7.1
startup-script: [2018-01-25 09:53:27 +0000] [8883] [INFO] Listening at: http://0.0.0.0:8080 (8883)
startup-script: [2018-01-25 09:53:27 +0000] [8883] [INFO] Using worker: sync
startup-script: [2018-01-25 09:53:27 +0000] [8886] [INFO] Booting worker with pid: 8886
"
}


gcloudcheck() {
  if hash gcloudcheck 2>/dev/null; then
    deployment
  else
    # MACHINE_TYPE=`uname -m`
    # if [ ${MACHINE_TYPE} == 'x86_64' ]; then
    #   MACHINE_TYPE='x64'
    # else
    #   MACHINE_TYPE='x32'
    # fi

    # OS="`uname`"
    # case $OS in
    #   'Linux')
    #     if [ ${MACHINE_TYPE} == 'x86_64' ]; then
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-linux-x86_64.tar.gz
    #     else
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-linux-x86.tar.gz
    #     fi
    #     ;;
    #   'WindowsNT')
    #     if [ ${MACHINE_TYPE} == 'x86_64' ]; then
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-windows-x86_64-bundled-python.zip
    #     else
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-windows-x86-bundled-python.zip
    #     fi
    #     ;;
    #   'Darwin') 
    #     if [ ${MACHINE_TYPE} == 'x86_64' ]; then
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-darwin-x86_64.tar.gz
    #     else
    #       wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-186.0.0-darwin-x86.tar.gz
    #     fi
    #     ;;
    #   *) ;;
    # esac
    echo "Please download and install gcloud SDK from the address: https://cloud.google.com/sdk/downloads, then run the script again"
  fi
}

gcloudcheck


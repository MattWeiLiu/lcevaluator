# this script is designed for centos 7
sudo yum install -y https://centos7.iuscommunity.org/ius-release.rpm
sudo yum update
sudo yum install git
sudo yum install -y python36u python36u-libs python36u-devel python36u-pip

#gsutil -m cp -r gs://db_formosa_plastics/package/ .
git clone git@gitlab.com:jonathan_wang_9264/lcevaluator.git

# Install dependencies
sudo pip3 install --upgrade pip
sudo pip3 install -r requirement.txt

# start gunicorn server
gunicorn service:app --bind 0.0.0.0:8080

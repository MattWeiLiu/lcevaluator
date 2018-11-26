# Install dependencies
sudo pip3.6 install --upgrade pip
sudo pip3.6 install -r requirement.txt

# start gunicorn server
gunicorn service:app --bind 0.0.0.0:8080

# Install
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
## Create a user
```
source venv/bin/activate
python manage.py createsuperuser
```

## API Server
Needs https://github.com/goapunk/wine-cellar-api running to use the search

# Need Check
/opt/venv/bin/python /app/manage.py needcheck
45 10,13,19 * * *

# Articles
/opt/venv/bin/python /app/manage.py getarticles
20 * * * *

# Charity info
/opt/venv/bin/python /app/manage.py charityinfo
30 4 * * *
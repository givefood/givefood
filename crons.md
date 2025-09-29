## Need Check
/opt/venv/bin/python /app/manage.py needcheck<br>
45 8,12,18 * * *

## Articles
/opt/venv/bin/python /app/manage.py getarticles<br>
20 9-18 * * *

## Charity info
/opt/venv/bin/python /app/manage.py charityinfo<br>
30 4 * * *

# DB Worker
/opt/venv/bin/python /app/manage.py db_worker --batch --max-tasks 50<br>
* * * * *
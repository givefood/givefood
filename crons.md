# Scheduled Tasks

| Task Name     | Command                                                           | Schedule          |
|---------------|-------------------------------------------------------------------|-------------------|
| Need Check    | `/opt/venv/bin/python /app/manage.py needcheck`                  | `45 7,11,15,19 * * *` |
| Articles      | `/opt/venv/bin/python /app/manage.py getarticles`                | `20 9-20 * * *`   |
| Charity Info  | `/opt/venv/bin/python /app/manage.py charityinfo`                | `30 4 * * *`      |
| Task Worker   | `/opt/venv/bin/python /app/manage.py db_worker --batch --max-tasks 50` | `*/5 * * * *`     |
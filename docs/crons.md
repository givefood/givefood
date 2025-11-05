# Scheduled Tasks

| Task Name           | Command                                                                        | Schedule              | Description                    |
|---------------------|--------------------------------------------------------------------------------|-----------------------|--------------------------------|
| Need Check          | `/opt/venv/bin/python /app/manage.py needcheck`                               | `45 7,11,15,19 * * *` | 4x daily (7:45, 11:45, 15:45, 19:45) |
| Articles            | `/opt/venv/bin/python /app/manage.py getarticles`                             | `20 8-22/2 * * *`     | Every 2 hours from 8:20-22:20  |
| Charity Info        | `/opt/venv/bin/python /app/manage.py charityinfo`                             | `30 5 * * *`          | Daily at 5:30 AM               |
| Dump                | `/opt/venv/bin/python /app/manage.py dump`                                    | `30 4 * * *`          | Daily at 4:30 AM               |
| Days Between Needs  | `/opt/venv/bin/python /app/manage.py days_between_needs`                      | `30 3 * * 0`           | Weekly on Sunday at 3:30 AM    |
| Task Worker         | `/opt/venv/bin/python /app/manage.py db_worker --batch --max-tasks 50 --queue-name *` | `* * * * *`         | Every 1 minute                |

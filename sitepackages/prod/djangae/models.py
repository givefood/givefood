from django.db import models

from djangae import patches


class CounterShard(models.Model):
    count = models.PositiveIntegerField()
    label = models.CharField(max_length=500)

    class Meta:
        app_label = "djangae"

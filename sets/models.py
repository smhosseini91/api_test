from django.db import models


class Set(models.Model):
    num_a = models.IntegerField('a')
    num_b = models.IntegerField('b')
    sum = models.IntegerField()

    class Meta:
        db_table = "sets"

    def __str__(self):
        return f'{self.num_b} + {self.num_b} = {self.sum}'

    def to_dict(self):
        return {
            'a': self.num_a,
            'b': self.num_b,
        }

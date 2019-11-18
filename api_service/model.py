from mongoengine import Document
from mongoengine.fields import *


def to_snake_case(name):
    return name.lower().strip().replace(" ", "_")


class Property(Document):
    label = StringField(required=True)
    primary_name = StringField(required=True, unique=True)
    level = StringField(required=True)
    description = StringField(required=True)

    synonyms = ListField(field=StringField())
    deprecate = BooleanField(default=False)

    def clean(self):

        self.primary_name = to_snake_case(self.primary_name)
        map(to_snake_case, self.synonyms)


class ControlledVocabulary(Document):
    deprecate = BooleanField(default=False)

    primary_name = StringField(required=True, unique=True)
    items = ListField(field=ListField(field=StringField), max_length=2)
    synonyms = ListField(field=StringField())
    description = StringField(required=True)

    def clean(self):
        self.primary_name = to_snake_case(self.primary_name)

        map(to_snake_case, self.synonyms)

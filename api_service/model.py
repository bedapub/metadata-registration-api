from bson import ObjectId

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *


def to_snake_case(name):
    return name.lower().strip().replace(" ", "_")


""" Controlled vocabulary model
    
    A  controlled vocabulary contains a `label` and a `name` which is displayed to the end user (external 
    representation) and  is used for the internal representation, respectively. The model ensures that the `name` is 
    converted to snake case.
    
    The description of the controlled vocabulary describes its purpose.
    
    The items contains a list of embedded items. An item stores an allowed vocabularies.
"""


class CvItem(EmbeddedDocument):
    """ An item in the list of controlled vocabularies """
    label = StringField(required=True)
    name = StringField(required=True)

    def clean(self):
        self.name = to_snake_case(self.name)


class ControlledVocabulary(Document):
    label = StringField(required=True)
    name = StringField(required=True, unique=True)

    description = StringField(required=True)

    items = ListField(EmbeddedDocumentField(CvItem), required=True)

    # Instead of removing, we deprecate
    deprecate = BooleanField(default=False)

    def clean(self):
        self.name = to_snake_case(self.name)


""" Property model
    
    A property contains a `label` and a `name` which is displayed to the end user (external representation) and  is used 
    for the internal representation, respectively. The model ensures that the `name` is converted to snake case.
    
    The synonym is a list of alternative labels.
    
    A property is assigned to a level in the property hierarchy (e.g. Study, Sample).
    
    The description of the property clarifies its purpose.
    
    The `vocabulary_type` is nested into the property and defines the 
    data type of the input. If the data type is a controlled vocabulary, the `controlled_vocabulary` references to 
    an entry in the controlled vocabulary model.
"""


class VocabularyType (EmbeddedDocument):
    """ Defines which type of vocabulary (e.g. text, numeric, controlled vocabulary) is allowed. """
    data_type = StringField(required=True)
    controlled_vocabulary = ReferenceField(ControlledVocabulary)

    def clean(self):
        if not ObjectId.is_valid(self.controlled_vocabulary):
            self.controlled_vocabulary = None


class Property(Document):
    label = StringField(required=True)
    name = StringField(required=True, unique=True)
    synonyms = ListField(field=StringField())

    level = StringField(required=True)
    description = StringField(required=True)

    vocabulary_type = EmbeddedDocumentField(VocabularyType)

    # Instead of removing, we deprecate
    deprecate = BooleanField(default=False)

    def clean(self):

        self.name = to_snake_case(self.name)
        map(to_snake_case, self.synonyms)


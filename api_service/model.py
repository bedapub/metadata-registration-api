from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *


def to_snake_case(name):
    """ Convert a string into an internal representation (no leading and trailing whitespace, and intermediate
    whitespace replaced with underscore)

    :param name:
    :return: name in snake_case or None
    """
    if name:
        return name.lower().strip().replace(" ", "_")

# ----------------------------------------------------------------------------------------------------------------------


""" Abstract model

A Base class for all top-level documents. 

A model contains a `label` and a `name` which is displayed to the end user (external representation) and  is used for 
the internal representation, respectively. The model ensures that the `name` is converted to snake case.

Instead of deleting entries, they are deprecated.
"""

class DeprecateDocument(Document):
    label = StringField(required=True)
    name = StringField(required=True, unique=True)
    deprecate = BooleanField(default=False)

    def clean(self):
        self.name = to_snake_case(self.name)

    meta = {'allow_inheritance': True, 'abstract': True}


""" Controlled vocabulary model

The description of the controlled vocabulary describes its purpose.
The items contains a list of embedded items. An item stores an allowed vocabularies.
"""


class CvItem(EmbeddedDocument):
    """ An item in the list of controlled vocabularies """
    label = StringField(required=True)
    name = StringField(required=True)
    description = StringField()
    synonyms = ListField(field=StringField())


class ControlledVocabulary(DeprecateDocument):
    description = StringField(required=True)

    items = ListField(EmbeddedDocumentField(CvItem), required=True)


""" Property model
    
The synonym is a list of alternative labels.
    
A property is assigned to a level in the property hierarchy (e.g. Study, Sample).
    
The description of the property clarifies its purpose.
    
The `vocabulary_type` is nested into the property and defines the data type of the input. If the data type is a 
controlled vocabulary, the `controlled_vocabulary` references to an entry in the controlled vocabulary model.
"""


class VocabularyType (EmbeddedDocument):
    """ Defines which type of vocabulary (e.g. text, numeric, controlled vocabulary) is allowed. """
    data_type = StringField(required=True)
    controlled_vocabulary = ReferenceField(ControlledVocabulary)

    def clean(self):
        if not ObjectId.is_valid(self.controlled_vocabulary):
            self.controlled_vocabulary = None


class Property(DeprecateDocument):
    synonyms = ListField(field=StringField())

    level = StringField(required=True)
    description = StringField(required=True)

    vocabulary_type = EmbeddedDocumentField(VocabularyType)

    def clean(self):
        map(to_snake_case, self.synonyms)

# ----------------------------------------------------------------------------------------------------------------------


""" Form model

A form contains fields. A field can accept an entry.
"""


class FormField(EmbeddedDocument):
    label = StringField()

    # Only used for administrative forms (not used for the study registration)
    name = StringField()
    # Reference to the property
    property = ReferenceField(Property)

    description = StringField()
    class_name = StringField(required=True)
    args = ListField(StringField())
    kwargs = DictField()

    def clean(self):
        if self.property:
            self.name = ""


class Form(DeprecateDocument):
    fields = EmbeddedDocumentListField(FormField)
    description = StringField(required=True)

# ----------------------------------------------------------------------------------------------------------------------


""" Study model
"""


class Field(EmbeddedDocument):
    label = StringField(required=True)
    property = ReferenceField(Property)
    # TODO: Check if correct type
    value = GenericEmbeddedDocumentField()


class Status(EmbeddedDocument):
    name = StringField()


class Study(DeprecateDocument):
    fields = EmbeddedDocumentListField(Field)
    status = EmbeddedDocumentField(Status)



# ----------------------------------------------------------------------------------------------------------------------


""" User model
"""


class User(Document):
    firstname = StringField(required=True)
    lastname = StringField(required=True)

    email = EmailField(required=True)
    password = StringField(required=True)
    is_active = BooleanField(required=True, default=True)


    def clean(self):
        """ Called before data is inserted into the database """

        # check if password looks like hashed
        is_hashed = lambda password: len(password) == 93 and password.startswith("pbkdf2:sha256:")

        # Hash password if it is not already hashed.
        if not is_hashed(self.password_hash):
            self.password_hash = generate_password_hash(self.password_hash)

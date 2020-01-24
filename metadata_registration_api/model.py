from werkzeug.security import generate_password_hash

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *


"""
This module defines document object mapping (DOM) of a set of administrative resources. 

The description of a model clarifies its purpose. The `synonyms` are a list of alternative labels. These alternative 
labels can be used to customize the external representation.
"""


def to_snake_case(name):
    """ Convert a string into an internal representation (no leading and trailing whitespace, and intermediate
    whitespace replaced with underscore)

    :param name: a given name
    :return: name in snake_case or None
    """
    if name:
        return name.lower().strip().replace(" ", "_")


# ----------------------------------------------------------------------------------------------------------------------

class TopLevelDocument(Document):
    """Base class for all top level documents

    All top level documents have a `label`, a `name` and a `deprecated` flag. The `label` is for displaying to the
    end user (external representation) and the `name` is used by the machine (internal representation). The name is
    expected to be unique for the model. To ensures that the `name` is converted to snake case before it is inserted
    into the database. The `deprecated` flag indicates if a document is no longer needed (alternative to delete it)
    """
    label = StringField(required=True)
    name = StringField(required=True, unique=True)
    deprecated = BooleanField(default=False)

    def clean(self):
        self.name = to_snake_case(self.name)

    meta = {'allow_inheritance': True, 'abstract': True}

# ----------------------------------------------------------------------------------------------------------------------


class CvItem(EmbeddedDocument):
    """An item in the list of controlled vocabularies"""
    label = StringField(required=True)
    name = StringField(required=True)
    description = StringField()
    synonyms = ListField(field=StringField())


class ControlledVocabulary(TopLevelDocument):
    """Model for a controlled vocabulary.

    A controlled vocabulary contains a list of possible items. See :class:`Property`.
    """
    description = StringField(required=True)
    items = ListField(EmbeddedDocumentField(CvItem), required=True)

# ----------------------------------------------------------------------------------------------------------------------


class VocabularyType(EmbeddedDocument):
    """ Model which defines the allowed vocabulary.

    It is used to validate user input. If the data type is `ctrl_voc`, only the items of :class:`ControlledVocabulary`
    are allowed.
    """
    data_type = StringField(required=True)
    controlled_vocabulary = ReferenceField(ControlledVocabulary)


class Property(TopLevelDocument):
    """ Model for a property

    A property is assigned to a level.
    """
    synonyms = ListField(field=StringField())

    level = StringField(required=True)
    description = StringField(required=True)

    value_type = EmbeddedDocumentField(VocabularyType)

    def clean(self):
        map(to_snake_case, self.synonyms)


# ----------------------------------------------------------------------------------------------------------------------


class DataObject(EmbeddedDocument):
    class_name = StringField()
    property = ReferenceField(Property)
    args = DictField()
    kwargs = DictField()
    fields = ListField(EmbeddedDocumentField("FormField"))


class DataObjects(EmbeddedDocument):
    objects = EmbeddedDocumentListField(DataObject)


class FormField(EmbeddedDocument):
    label = StringField()
    # Reference to the property
    property = ReferenceField(Property)
    description = StringField()
    class_name = StringField(required=True)
    args = GenericEmbeddedDocumentField(choices=[DataObjects, DictField])
    kwargs = DictField()

    # Used for nested forms
    name = StringField()
    fields = ListField(EmbeddedDocumentField("FormField"))

    def clean(self):
        if self.property:
            # TODO Empty string or None?
            self.name = ""


class Form(TopLevelDocument):
    """MongoDB representation of a FlaskForm

    The form contains multiple fields.
    """
    fields = EmbeddedDocumentListField(FormField)
    description = StringField(required=True)


# ----------------------------------------------------------------------------------------------------------------------


class StudyEntry(EmbeddedDocument):
    property = ReferenceField(Property)
    # TODO: Check if correct type
    value = StringField()


class Status(EmbeddedDocument):
    name = StringField()


class Study(TopLevelDocument):
    entries = EmbeddedDocumentListField(StudyEntry)
    status = EmbeddedDocumentField(Status)


# ----------------------------------------------------------------------------------------------------------------------


class User(Document):
    firstname = StringField(required=True)
    lastname = StringField(required=True)

    email = EmailField(required=True, unique=True)
    password = StringField(required=True)
    is_active = BooleanField(required=True, default=True)

    def clean(self):
        """ Called before data is inserted into the database """

        # check if password looks like hashed
        def is_hashed(password):
            return len(password) == 93 and password.startswith("pbkdf2:sha256:")

        # Hash password if it is not already hashed.
        if not is_hashed(self.password):
            self.password = generate_password_hash(self.password)

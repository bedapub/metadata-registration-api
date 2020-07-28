from dataclasses import dataclass
from datetime import datetime
from typing import Optional

PRIMITIVES = (bool, int, float, str)
PRIMITIVES_LIST = (*PRIMITIVES, list)


class FormatConverter:
    """Class responsible for converting between api format and form format.

    API FORMAT
    ----------
    The api format consists of a list of dictionaries. Each dictionary has two keys: property and value. The value of
    the property is the property id. The second key (value) can take four different formats:
        1. primitive data type (string, int, float, boolean)
        2. list of primitive data types
        3. dictionary (representing a FormField)
        4. list of dictionary (representing a list of FormField)

    FORM FORMAT
    -----------
    The form format is designed such that it can be directly passed to a wtf form. It is a dictionary with the
    property names as key and the given data as value. The value can take four different formats:
        1. primitive data type (string, int, float, boolean)
        2. list of primitive data types
        3. dictionary (representing a FormField)
        4. list of dictionary (representing a list of FormField)
    """

    def __init__(self, mapper: dict, key_name: str = "property", value_name: str = "value"):
        """
        :param key_name: name under which the key the property id is stored
        :param value_name: name under which the user input is stored
        :param mapper: dict which converts between the property id and property name
        """
        self.key_name = key_name
        self.value_name = value_name
        self.mapper = mapper

        self.entries = []

    def __repr__(self):
        return f"<{self.__class__.__name__} (key name: {self.key_name}, value name: {self.value_name}, " \
               f"mapper: {self.mapper})>"

    def add_api_format(self, data):
        """
        :param data: data in api format
        :return: self
        """
        self.entries = []
        for entry in data:
            self.entries.append(Entry(self).add_api_format(entry))

        return self

    def add_form_format(self, data):
        """
        :param data: data in form format
        :return: self
        """
        self.entries = [Entry(self).add_form_format(key=key, value=value) for key, value in data.items()]
        return self

    def get_api_format(self):
        """
        :return: Returns data in api format
        """
        return [{self.key_name: entry.prop_id, self.value_name: entry.get_api_format()} for entry in self.entries]

    def get_form_format(self):
        """
        :return: Returns data in form format
        """
        return {entry.prop_name: entry.get_form_format() for entry in self.entries}


class Entry:

    def __init__(self, converter):
        self.converter = converter

        self.prop_id = None
        self.prop_name = None
        self.value = None

    def __repr__(self):
        return f"<Entry(property: {self.prop_name}, id: {self.prop_id}, value: {self.value})>"

    def add_api_format(self, data):
        self.prop_id = data[self.converter.key_name]
        self.prop_name = self.converter.mapper[self.prop_id]

        def convert_value(value):
            if type(value) in PRIMITIVES:  # simple value
                return value
            elif isinstance(value, list):
                if all(type(entry) in PRIMITIVES for entry in value):  # list of simple values
                    return value
                elif all(isinstance(entry, dict) for entry in value):  # FormField
                    return NestedEntry(self.converter).add_api_format(value)
                elif all(isinstance(entry, list) for entry in value):  # FieldList of FormField
                    return NestedListEntry(self.converter).add_api_format(value)

        self.value = convert_value(data[self.converter.value_name])

        return self

    def add_form_format(self, key, value):
        self.prop_name = key
        self.prop_id = self.converter.mapper[key]

        def convert_value(value):
            if type(value) in PRIMITIVES:
                return value
            elif type(value) is dict:
                return NestedEntry(self.converter).add_form_format(value)
            elif isinstance(value, list):
                if all(type(entry) in PRIMITIVES for entry in value):
                    return value
                if all(type(entry) is dict for entry in value):
                    return NestedListEntry(self.converter).add_form_format(value)

        self.value = convert_value(value)

        return self

    def get_api_format(self):
        if type(self.value) in PRIMITIVES_LIST:
            return self.value

        return self.value.get_api_format()

    def get_form_format(self):
        if type(self.value) in PRIMITIVES_LIST:
            return self.value

        return self.value.get_form_format()


class NestedEntry:

    def __init__(self, converter):
        self.converter = converter
        self.value = None

    def __repr__(self):
        return f"<{self.__class__.__name__} (value: {self.value})>"

    def add_api_format(self, data):
        self.value = [Entry(self.converter).add_api_format(entry) for entry in data]
        return self

    def add_form_format(self, data):
        self.value = [Entry(self.converter).add_form_format(key=key, value=value)
                      for key, value in data.items()]
        return self

    def get_api_format(self):
        return [{self.converter.key_name: entry.prop_id, self.converter.value_name: entry.get_api_format()}
                for entry in self.value]

    def get_form_format(self):
        return {entry.prop_name: entry.get_form_format() for entry in self.value}


class NestedListEntry:

    def __init__(self, converter):
        self.converter = converter
        self.value = None

    def __repr__(self):
        return f"<{self.__class__.__name__} (value: {self.value})>"

    def add_api_format(self, data):
        self.value = [NestedEntry(self.converter).add_api_format(item) for item in data]
        return self

    def add_form_format(self, data):
        self.value = [NestedEntry(self.converter).add_form_format(item) for item in data]
        return self

    def get_api_format(self):
        return [entry.get_api_format() for entry in self.value]

    def get_form_format(self):
        return [entry.get_form_format() for entry in self.value]


@dataclass()
class ChangeLog:
    action: str
    user_id: str
    timestamp: datetime
    manual_user: Optional[str] = None

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value}


class MetaInformation:

    def __init__(self, state: str, change_log=None):

        if change_log and not isinstance(change_log, list):
            raise AttributeError("Change log has to be an instance of list")

        self.state = state
        self.change_log = change_log if change_log else list()

    def add_log(self, log: ChangeLog):
        self.change_log.append(log.to_dict())

    def to_json(self):
        return {
            "state": self.state,
            "change_log": self.change_log
        }




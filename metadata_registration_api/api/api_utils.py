from datetime import datetime
from dataclasses import dataclass
from typing import Optional


class StudyEntry:
    """Helper class to convert between the input and form format

        The input format consists of a property id and a value. The form format consists of a name and a value. This
        class converts between the two formats.

        The value supports several formats. It can contain a value or a list of entries.

        entry: {
            prop: 123
            value: abc
        }

        entry: {
            prop: 123
            value: [{prop: 123, value: abc}, {prop: 123, value: abc}]
        }

        entry: {
           prop: 123
           value: [{prop: 123, value: [{}, ...]}, {prop: 123, value: [{}, ...]}]
        }
    """

    def __init__(self, value, identifier=None, name=None):
        """
        :param value:
        :param identifier:
        :param name:
        """
        self.value = value
        self.identifier = identifier
        self.name = name

    def set_name_by_id(self, map):
        """ Set the name of the entry based on the identifier given in the map"""
        if not self.identifier:
            raise Exception(f"{self.set_name_by_id.__name__} cannot be used. Identifier of entry not set")

        if isinstance(self.value, list):
            for entry in self.value:
                entry.set_name_by_id(map)

        self.name = map[self.identifier]

    def set_id_by_name(self, map):
        """Set the identifier of the entry based on the name given in the map"""
        if not self.name:
            raise Exception(f"{self.set_id_by_name.__name__} cannot be used. Name of entry not set")

        if isinstance(self.value, list):
            for entry in self.value:
                entry.set_name_by_id(self.name, map)

        self.identifier = map[self.name]

    def form_format(self):
        """Convert to a dictionary in form format"""
        if isinstance(self.value, list):
            my_list = []
            for entry in self.value:
                if isinstance(entry.value, list):
                    my_list_2 = {}
                    for item in entry.value:
                        my_list_2[item.name] = item.form_format()
                    my_list.append({entry.name: my_list_2})
                else:
                    my_list.append(entry.value)
            return my_list
        else:
            return self.value

    def input_format(self):
        raise NotImplementedError


def json_entry_to_obj(entry_data, key_name, value_name):
    if isinstance(entry_data[value_name], list):
        my_list = []
        for item in entry_data[value_name]:
            my_list.append(json_entry_to_obj(item, key_name, value_name))
        return StudyEntry(identifier=entry_data[key_name], value=my_list)
    else:
        return StudyEntry(identifier=entry_data[key_name], value=entry_data[value_name])


def json_input_to_form_format(json_data, mapper, key_name="property", value_name="value"):
    """Convert json input format into form format.

    The conversation is achieved through an object.

    :param json_data:
    :param mapper: dict with id as key and name as value
    :param key_name:
    :param value_name:
    :return: dict with name as key and value in value
    """
    entries = []

    for data in json_data:
        entry = json_entry_to_obj(data, key_name=key_name, value_name=value_name)
        entry.set_name_by_id(mapper)
        entries.append(entry)

    return {entry.name: entry.form_format() for entry in entries}


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




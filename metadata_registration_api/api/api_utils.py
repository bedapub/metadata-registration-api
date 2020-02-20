
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
                my_list_2 = {}
                for item in entry.value:
                    my_list_2[item.name] = item.form_format()
                my_list.append({entry.name: my_list_2})
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


def json_entries_to_objs(data_json, map, key_name="property", value_name="value"):
    entries = []
    for data in data_json:
        entry = json_entry_to_obj(data, key_name=key_name, value_name=value_name)
        entry.set_name_by_id(map)

        entries.append(entry)
    return entries



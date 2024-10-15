from os.path import exists, getsize
from os import access, R_OK
from tools.nwn_editors.bic import *


class NPCData:
    def __init__(self):
        self.label = 0
        self.value = 0
        self.loc = 0
        self.data_type = 0


class Header:
    def __init__(self):
        self.file_type = None
        self.file_version = None
        self.struct_offset = None
        self.struct_count = None
        self.field_offset = None
        self.field_count = None
        self.label_offset = None
        self.label_count = None
        self.field_data_offset = None
        self.field_data_count = None
        self.field_indices_offset = None
        self.field_indices_count = None
        self.list_indices_offset = None
        self.list_indices_count = None


class Struct:
    def __init__(self):
        self.type = 0
        self.data_or_offset = 0
        self.field_cnt = 0


class Field:
    def __init__(self):
        self.type = 0
        self.data_or_offset = 0
        self.label_index = 0

class Entry:
    def __init__(self):
        self.entry_list = list()
        self.code = 0
        self.index = 0
        self.num_elements = 0


class Element:
    def __init__(self):
        self.elm_type = 0
        self.name_index = 0
        self.data = None
        self.num_items = 0
        self.elem_list = list()


class Resource:
    def __init__(self):
        self.res_data_offset = 0
        self.file_length = 0


class Character:

    def __init__(self):
        self.signature = None
        self.file = None
        self.file_name = ""
        self.file_type = ""
        self.file_version = ""
        self.description = ""
        self.file_size = 0
        self.data_offset = 0
        self.url = ""
        self.title = ""
        self.num_res = 0
        self.num_elements = 0
        self.entries = list()
        self.elements = list()
        self.modified_data = None
        self.resources = list()
        self.header = Header()
        self.labels = list()
        self.structs = list()
        self.fields = list()
        self.npc_data = dict()

    def _open_file(self, a_file_name, modes):
        self.file_name = a_file_name
        self.modes = modes

        if self.file_name == "":
            return False

        elif not exists(self.file_name):
            return False

        elif not access(self.file_name, R_OK):
            return False
        else:
            self.file_size = getsize(self.file_name)
            self.file_name = self.file_name
            self.file = open(self.file_name, self.modes)

    def _get_header(self):
        self.header.file_type = self.file.read(4)
        self.header.file_version = self.file.read(4)
        self.header.struct_offset = int.from_bytes(self.file.read(4), "little")
        self.header.struct_count = int.from_bytes(self.file.read(4), "little")
        self.header.field_offset = int.from_bytes(self.file.read(4), "little")
        self.header.field_count = int.from_bytes(self.file.read(4), "little")
        self.header.label_offset = int.from_bytes(self.file.read(4), "little")
        self.header.label_count = int.from_bytes(self.file.read(4), "little")
        self.header.field_data_offset = int.from_bytes(self.file.read(4), "little")
        self.header.field_data_count = int.from_bytes(self.file.read(4), "little")
        self.header.field_indices_offset = int.from_bytes(self.file.read(4), "little")
        self.header.field_indices_count = int.from_bytes(self.file.read(4), "little")
        self.header.list_indices_offset = int.from_bytes(self.file.read(4), "little")
        self.header.list_indices_count = int.from_bytes(self.file.read(4), "little")

    def _get_labels(self):
        self.file.seek(self.header.label_offset)
        for count in range(self.header.label_count):
            label = self.file.read(16).decode().rstrip('\x00')
            self.labels.append(label)

    def _get_structs(self):
        self.file.seek(self.header.struct_offset)
        for count in range(self.header.struct_count):
            struct = Struct()
            struct.type = int.from_bytes(self.file.read(4), "little")
            struct.data_or_offset = int.from_bytes(self.file.read(4), "little")
            struct.field_cnt = int.from_bytes(self.file.read(4), "little")
            self.structs.append(struct)

    def _get_fields(self):
        self.file.seek(self.header.field_offset)
        for count in range(self.header.field_count):
            field = Field()
            field.type = int.from_bytes(self.file.read(4), "little")
            field.label_index = int.from_bytes(self.file.read(4), "little")
            field.data_or_offset = int.from_bytes(self.file.read(4), "little")
            # Simple data types
            self.fields.append(field)
        # Read field data
        i = 0
        for field in self.fields:
            npc_data = NPCData()
            # Simple fields
            if field.type in [0, 1, 2, 3, 4, 5, 8]:
                npc_data.loc = self.file.tell()
                npc_data.data_type = field.type
                field.data = field.data_or_offset
                npc_data.label = self.labels[field.label_index]
                if npc_data.label == "Race":
                    npc_data.value = get_race(field.data)
                self.npc_data[npc_data.label] = npc_data

            else:
                # Subset of complex fields (first name, last name and description)
                if field.label_index in [1, 2, 3]:
                    offset = self.header.field_data_offset + field.data_or_offset
                    npc_data.loc = offset
                    self.file.seek(offset)

                    # TODO: Add multiple string support: currently this code only supports 1 string in the string array
                    total_size = int.from_bytes(self.file.read(4), "little")
                    string_ref = int.from_bytes(self.file.read(4), "little")
                    string_count = int.from_bytes(self.file.read(4), "little")
                    string_id = int.from_bytes(self.file.read(4), "little")
                    string_len = int.from_bytes(self.file.read(4), "little")
                    string = self.file.read(string_len)
                    npc_data.label = self.labels[field.label_index]
                    try:
                        npc_data.value = string.decode()
                    except:
                        # TODO: Figure out why there are bad description items in the field table
                        continue
                    self.npc_data[npc_data.label] = npc_data
            i = i + 1

    def load_file(self, a_filename):

        self._open_file(a_filename, "rb")
        self.file.seek(0)
        self._get_header()
        sig_str = self.header.file_type.decode()
        self.file_type = sig_str.replace(" ", "")
        self.file_version = self.header.file_version
        self._get_labels()
        self._get_structs()
        self._get_fields()

        self.data_offset = self.header.res_data
        self.num_res = self.header.num_entries
        self.num_elements = self.header.num_elements

        # if file type is ERF no URL,TITLE,DESCRIPTION
        # if file type is MOD only a description
        # if file type is HAK we have URL Title and description
        if self.file_type != 'ERF':
            self.file.seek(164)

        # Parse entries in the file
        for i in range(self.header.num_entries):
            entry = Entry()
            self.file.seek(self.header.first_entry + 12 * i)
            entry.code = int.from_bytes(self.file.read(4), "little")
            entry.index = int.from_bytes(self.file.read(4), "little")
            entry.num_elements = int.from_bytes(self.file.read(4), "little")
            if entry.num_elements > 1:
                self.file.seek(self.header.first_multimap + entry.index)

                for j in range(entry.num_elements):
                    entry.entry_list.append(int.from_bytes(self.file.read(4), "little"))
            else:
                entry.entry_list.append(entry.index)

            self.entries.append(entry)

        for i in range(self.header.num_elements):
            self.file.seek(self.header.first_element + 12 * i)
            element = Element()
            element.elm_type = int.from_bytes(self.file.read(4), "little")
            element.name_index = int.from_bytes(self.file.read(4), "little")
            element.data = int.from_bytes(self.file.read(4), "little")

            if element.elm_type == 10:  # Equipment Res Ref
                self.file.seek(self.header.first_variable + element.data)
                elm_len = int.from_bytes(self.file.read(4), "little")
                if elm_len > 0:
                    element.data = self.file.read(4)

            elif element.elm_type == 11:
                self.file.seek(self.header.first_variable + element.data)
                elm_len = int.from_bytes(self.file.read(1), "little")
                if elm_len > 0:
                    element.data = self.file.read(elm_len)
            elif element.elm_type == 12:  # Equipment Description
                self.file.seek(self.header.first_variable + element.data)
                num_bytes = int.from_bytes(self.file.read(4), "little")
                dialog_id = int.from_bytes(self.file.read(4), "little")
                lang_spec = int.from_bytes(self.file.read(4), "little")
                if lang_spec > 0:
                    lang = int.from_bytes(self.file.read(4), "little")
                    elem_len = int.from_bytes(self.file.read(4), "little")
                    if elem_len > 0:
                        element.data = self.file.read(elem_len)
            elif element.elm_type == 15:
                self.file.seek(self.header.first_list + element.data)
                num_items = int.from_bytes(self.file.read(4), "little")
                element.num_items = num_items

                for j in range(element.num_items):
                    element.elem_list.append(int.from_bytes(self.file.read(4), "little"))
            self.elements.append(element)

        # Reading general resource info
        self.file.seek(self.header.first_variable_name)
        resource = Resource()
        resource.res_data_offset = int.from_bytes(self.file.read(4), "little")
        resource.file_length = int.from_bytes(self.file.read(4), "little")

        for i in range(self.header.num_variable_name):
            res_name = self.file.read(16)
            ssv = 1 + 1
            self.resource.res_data_offset = int.from_bytes(self.file.read(4), "little")
            self.resources[i][resource.file_length] = int.from_bytes(self.file.read(4), "little")

        # self.resources[ResName]    = str_replace(chr(00),'',res_name);

        # reading resource data info */
        """ SSV: broken code
        self.file.seek(self.header[FileEntrie]);
        for i in range(self.num_res):
            resource = Resource()
            
            self.resource.res_data_offset = int.from_bytes(self.file.read(4))
            self.resource.file_length = int.from_bytes(self.file.read(4))
        } /* end for Numres */
        """
        return True


def ssv_run():
    from tkinter import filedialog
    filename = filedialog.askopenfilename()
    char = Character()
    char.load_file(filename)
ssv_run()

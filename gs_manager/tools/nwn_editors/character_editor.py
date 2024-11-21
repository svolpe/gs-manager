from os.path import exists, getsize
from os import access, R_OK, unlink
from .bic import *
import tempfile
import subprocess

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
        self.entry_list = []
        self.code = 0
        self.index = 0
        self.num_elements = 0


class Element:
    def __init__(self):
        self.elm_type = 0
        self.name_index = 0
        self.data = None
        self.num_items = 0
        self.elem_list = []


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
        self.entries = []
        self.elements = []
        self.modified_data = None
        self.resources = []
        self.header = Header()
        self.labels = []
        self.structs = []
        self.fields = []
        self.npc_data = {}

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
        for _count in range(self.header.label_count):
            label = self.file.read(16).decode().rstrip('\x00')
            self.labels.append(label)

    def _get_structs(self):
        self.file.seek(self.header.struct_offset)
        for _count in range(self.header.struct_count):
            struct = Struct()
            struct.type = int.from_bytes(self.file.read(4), "little")
            struct.data_or_offset = int.from_bytes(self.file.read(4), "little")
            struct.field_cnt = int.from_bytes(self.file.read(4), "little")
            self.structs.append(struct)

    def _get_fields(self):
        self.file.seek(self.header.field_offset)

        # Get list of all the fields meta data (type, index and offset)
        for _count in range(self.header.field_count):
            field = Field()
            field.type = int.from_bytes(self.file.read(4), "little")
            field.label_index = int.from_bytes(self.file.read(4), "little")
            field.data_or_offset = int.from_bytes(self.file.read(4), "little")
            # Simple data types
            self.fields.append(field)
        
        # Read field data
        # Read data stored in fields
        for field in self.fields:
            npc_data = NPCData()
            # Simple fields
            npc_data.label = self.labels[field.label_index]
            if field.type in [0, 1, 2, 3, 4, 5, 8]:
                npc_data.loc = self.file.tell()
                npc_data.data_type = field.type
                field.data = field.data_or_offset

                npc_data.value = (
                    get_race(field.data)
                    if npc_data.label in ["Race", "Gender"]
                    else field.data
                )
            elif field.label_index in [1, 2, 3]:
                offset = self.header.field_data_offset + field.data_or_offset
                npc_data.loc = offset
                self.file.seek(offset)

                # TODO: Add multiple string support: currently this code only supports 1 string in the string array
                _total_size = int.from_bytes(self.file.read(4), "little")
                _string_ref = int.from_bytes(self.file.read(4), "little")
                _string_count = int.from_bytes(self.file.read(4), "little")
                _string_id = int.from_bytes(self.file.read(4), "little")
                string_len = int.from_bytes(self.file.read(4), "little")
                string = self.file.read(string_len)
                npc_data.label = self.labels[field.label_index]
                try:
                    npc_data.value = string.decode()
                except Exception:
                    # TODO: Figure out why there are bad description items in the field table
                    continue
            # Get CRefs
            elif field.label_index in [47]:
                offset = self.header.field_data_offset + field.data_or_offset
                npc_data.loc = offset
                self.file.seek(offset)
                string_len = int.from_bytes(self.file.read(1), "little")
                string = self.file.read(string_len)
                try:
                    npc_data.value = string.decode()
                except Exception:
                    # TODO: Figure out why there are bad description items in the field table
                    continue
                npc_data.label = self.labels[field.label_index]

            # Store data in NPC Object
            self.npc_data[npc_data.label] = npc_data

    def load_file(self, a_filename):
        self.file_name = a_filename
        self._open_file(a_filename, "rb")
        self.file.seek(0)
        self._get_header()
        sig_str = self.header.file_type.decode()
        self.file_type = sig_str.replace(" ", "")
        self.file_version = self.header.file_version
        self._get_labels()
        self._get_structs()
        self._get_fields()
        self.file.close()
        
    def get_alignment(self):
        
        good_evil = self.npc_data["GoodEvil"].value
        lawful_chaotic = self.npc_data["LawfulChaotic"].value
        if lawful_chaotic <= 15: 
            align1 = "Chaotic"
        if lawful_chaotic > 15 and lawful_chaotic < 85 and good_evil >= 85 or good_evil <= 15: 
            align1 = "Neutral"
        if lawful_chaotic > 15 and lawful_chaotic < 85 and good_evil < 85 or good_evil > 15: 
            align1 = "True"
        if lawful_chaotic >= 85: 
            align1 = "Lawful"
        if good_evil <= 15:
            align2 = "Evil"
        if good_evil > 15 and good_evil < 85:
            align2 = "Neutral"
        if good_evil >= 85: 
            align2 = "Good"

        return f'{align1} {align2}';
    
    def _save_data(self, field, value):
        # Remove new line
        value = value.replace("\n", "")
        fp = tempfile.NamedTemporaryFile(mode='wt', delete=False, prefix="gsm_")
        fp.write(f"%char = '{self.file_name}';\n")
        fp.write(f"/{field} = '{value}';\n")
        fp.write(f"%char = '>';\n")
        fp.write(f"close %char;\n")

        fp.close()
        
        #Execute legacy Mono command
        arguments = [fp.name]
        command = ["Moneo", *arguments]
        subprocess.run(command, stdout=subprocess.PIPE)
        # Remove temp file
        unlink(fp.name)

    def _read_data_moneo(self, field):        
        fp = tempfile.NamedTemporaryFile(mode='wt', delete=False, prefix="gsm_")
        fp.write(f"%char = '{self.file_name}';\n")
        fp.write(f"print /{field};\n")
        fp.write(f"close %char;\n")

        fp.close()
        
        #Execute legacy Mono command
        arguments = [fp.name]
        command = ["Moneo", *arguments]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = proc.stdout.read()
        # Remove temp file
        unlink(fp.name)
        try:
            description = output.decode()
        except:
            description = "Error in reading character"
        return description

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
        self.loc_string = None  # Store full CExoLocString for text fields


class CExoLocString:
    """Handles CExoLocString structures in GFF files.

    A CExoLocString can contain multiple language-specific strings.
    Structure:
        - total_size (4 bytes): total size of the entire structure in bytes
        - string_ref (4 bytes): reference to dialog.tlk (-1 if unused)
        - string_count (4 bytes): number of language strings
        - For each string:
            - language_id (4 bytes): language identifier (0=English, etc.)
            - string_length (4 bytes): length of the string
            - string_data (variable): the actual string data
    """

    def __init__(self):
        self.total_size = 0
        self.string_ref = -1
        self.string_count = 0
        self.strings = {}  # {language_id: string}

    @classmethod
    def read_from_file(cls, file, offset):
        """Read a CExoLocString from a file at the given offset."""
        loc_string = cls()
        file.seek(offset)

        loc_string.total_size = int.from_bytes(file.read(4), "little")
        loc_string.string_ref = int.from_bytes(file.read(4), "little", signed=True)

        # Check if this is an empty CExoLocString (only 8 bytes: total_size + string_ref)
        if loc_string.total_size == 8:
            loc_string.string_count = 0
            return loc_string

        loc_string.string_count = int.from_bytes(file.read(4), "little")

        for _ in range(loc_string.string_count):
            language_id = int.from_bytes(file.read(4), "little")
            string_length = int.from_bytes(file.read(4), "little")
            string_data = file.read(string_length).decode('utf-8', errors='replace')
            loc_string.strings[language_id] = string_data

        return loc_string

    def get_string(self, language_id=0):
        """Get string for a specific language, defaults to English (0)."""
        if language_id in self.strings:
            return self.strings[language_id]
        # Return first available string if requested language not found
        if self.strings:
            return next(iter(self.strings.values()))
        return ""

    def set_string(self, text, language_id=0):
        """Set string for a specific language."""
        if text:
            self.strings[language_id] = text
            self.string_count = len(self.strings)
        else:
            # If setting empty string, remove it
            if language_id in self.strings:
                del self.strings[language_id]
            self.string_count = len(self.strings)
        self._calculate_size()

    def clear(self):
        """Clear all strings, making this an empty CExoLocString."""
        self.strings = {}
        self.string_count = 0
        self._calculate_size()

    def _calculate_size(self):
        """Calculate the total size of the structure."""
        if self.string_count == 0:
            # Empty CExoLocString: only total_size (4 bytes) + string_ref (4 bytes) = 8 bytes
            self.total_size = 8
        else:
            # 12 bytes for header (total_size, string_ref, string_count)
            size = 12
            for lang_id, string in self.strings.items():
                # 4 bytes for language_id, 4 bytes for string_length, plus string data
                size += 8 + len(string.encode('utf-8'))
            self.total_size = size

    def to_bytes(self):
        """Convert the CExoLocString to bytes for writing to file."""
        self._calculate_size()

        data = bytearray()
        data.extend(self.total_size.to_bytes(4, "little"))
        data.extend(self.string_ref.to_bytes(4, "little", signed=True))

        # Only write string_count and strings if there are any
        if self.string_count > 0:
            data.extend(self.string_count.to_bytes(4, "little"))

            for language_id, string in self.strings.items():
                string_bytes = string.encode('utf-8')
                data.extend(language_id.to_bytes(4, "little"))
                data.extend(len(string_bytes).to_bytes(4, "little"))
                data.extend(string_bytes)

        return bytes(data)


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

            # Skip if we already have this field (only keep first occurrence)
            # This prevents inventory item fields from overwriting character fields
            if npc_data.label in self.npc_data:
                continue

            if field.type in [0, 1, 2, 3, 4, 5, 8]:
                npc_data.loc = self.file.tell()
                npc_data.data_type = field.type
                field.data = field.data_or_offset

                npc_data.value = (
                    get_race(field.data)
                    if npc_data.label in ["Race", "Gender"]
                    else field.data
                )
            elif field.type == 12:  # CExoLocString type
                offset = self.header.field_data_offset + field.data_or_offset
                npc_data.loc = offset
                npc_data.data_type = field.type

                try:
                    # Use CExoLocString to properly read all language strings
                    npc_data.loc_string = CExoLocString.read_from_file(self.file, offset)
                    npc_data.value = npc_data.loc_string.get_string()
                except Exception as e:
                    # Handle corrupted or invalid string data
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

    def save_string_field(self, field_name, new_value, language_id=0):
        """Save a string field (like Description, FirstName, LastName) to the BIC file.

        Args:
            field_name: Name of the field to update (e.g., 'Description', 'FirstName')
            new_value: New string value
            language_id: Language ID (0 for English)

        Returns:
            True if successful, False otherwise
        """
        if field_name not in self.npc_data:
            return False

        npc_data = self.npc_data[field_name]

        # Check if this field has a CExoLocString
        if npc_data.loc_string is None:
            return False

        # Calculate the OLD size from the actual data structure (not the stored total_size)
        # This handles cases where tools like Moneo wrote incorrect total_size fields
        old_loc_string = npc_data.loc_string
        old_calculated_size = 12  # header (total_size + string_ref + string_count)
        for lang_id, string in old_loc_string.strings.items():
            old_calculated_size += 8 + len(string.encode('utf-8'))  # lang_id + str_len + data
        if old_loc_string.string_count == 0:
            old_calculated_size = 8  # empty CExoLocString

        # Update the string in the CExoLocString object
        npc_data.loc_string.set_string(new_value, language_id)
        new_bytes = npc_data.loc_string.to_bytes()
        new_size = len(new_bytes)

        # Read the entire file into memory
        with open(self.file_name, 'rb') as f:
            file_data = bytearray(f.read())

        offset = npc_data.loc

        # Check if sizes match based on ACTUAL data size
        if old_calculated_size == new_size:
            # Replace the data at the location (using old_calculated_size for how many bytes to replace)
            # This handles cases where the stored total_size field was wrong
            file_data[offset:offset+old_calculated_size] = new_bytes

            # Write back to file
            with open(self.file_name, 'wb') as f:
                f.write(file_data)

            # Update the in-memory value
            npc_data.value = new_value
            return True
        else:
            # Size mismatch - need to rebuild the field data section
            # For now, return False to indicate this case needs special handling
            # In future, we could implement full GFF reconstruction
            raise ValueError(
                f"String size changed from {old_calculated_size} to {new_size} bytes. "
                f"This requires rebuilding the entire field data section, which is not yet implemented."
            )

    def save_description(self, new_description):
        """Convenience method to save the character description.

        Args:
            new_description: New description text

        Returns:
            True if successful, False otherwise
        """
        return self.save_string_field('Description', new_description)
    
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

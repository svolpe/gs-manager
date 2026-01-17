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
        self.field_index = None  # Track which field this data came from


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

        # Validate string_count - if it's unreasonably large, this is likely corrupted or wrong field type
        # NWN typically has only a few language strings (max 20-30 languages in reality)
        if loc_string.string_count > 100:
            raise ValueError(f"Invalid CExoLocString: string_count={loc_string.string_count} is unreasonably large")

        for _ in range(loc_string.string_count):
            language_id = int.from_bytes(file.read(4), "little")
            string_length = int.from_bytes(file.read(4), "little")

            # Validate string length as well
            if string_length > 1000000:  # 1MB max per string
                raise ValueError(f"Invalid CExoLocString: string_length={string_length} is unreasonably large")

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
        """Calculate the total size of the structure.

        Per GFF spec, total_size is the size of data AFTER the total_size field itself.
        """
        if self.string_count == 0:
            # Empty CExoLocString: total_size excludes itself, so just string_ref = 4 bytes
            # (string_count is not written when empty)
            self.total_size = 4
        else:
            # string_ref (4) + string_count (4) = 8 bytes base
            size = 8
            for lang_id, string in self.strings.items():
                # 4 bytes for language_id, 4 bytes for string_length, plus string data
                size += 8 + len(string.encode('utf-8'))
            self.total_size = size

    def to_bytes(self, preserve_total_size=False):
        """Convert the CExoLocString to bytes for writing to file.

        Args:
            preserve_total_size: If True, keep the original total_size value instead
                               of recalculating it. This is needed for files where
                               other fields share/overlap the CExoLocString data.
        """
        if not preserve_total_size:
            self._calculate_size()

        data = bytearray()
        data.extend(self.total_size.to_bytes(4, "little"))
        data.extend(self.string_ref.to_bytes(4, "little", signed=True))

        # Write string_count if total_size > 4 (format includes it) OR if there are strings
        # This handles empty CExoLocStrings that still have string_count=0 in the file
        if self.total_size > 4 or self.string_count > 0:
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
        for idx, field in enumerate(self.fields):
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
            elif field.type == 10:  # CExoString type
                offset = self.header.field_data_offset + field.data_or_offset
                npc_data.loc = offset
                npc_data.data_type = field.type

                try:
                    self.file.seek(offset)
                    string_len = int.from_bytes(self.file.read(4), "little")
                    string_data = self.file.read(string_len)
                    npc_data.value = string_data.decode('utf-8', errors='replace')
                except Exception as e:
                    # Handle corrupted or invalid string data
                    continue
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
            npc_data.field_index = idx
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

    def _rebuild_field_data_section(self, field_name, new_value, language_id=0):
        """Rebuild the entire field data section when a field size changes.

        This is necessary when a CExoString or CExoLocString changes size, as all subsequent
        field offsets need to be updated.
        """
        # Read entire file
        with open(self.file_name, 'rb') as f:
            file_data = bytearray(f.read())

        # Build a list of all fields that have data in the field data section
        # We need to track their order and rebuild them
        field_data_items = []
        processed_offsets = set()  # Track which offsets we've already processed
        claimed_ranges = []  # Track (start, end) byte ranges claimed by type 10/12 fields

        def is_offset_claimed(offset):
            """Check if an offset falls within any claimed range."""
            for start, end in claimed_ranges:
                if start <= offset < end:
                    return True
            return False

        for idx, field in enumerate(self.fields):
            label = self.labels[field.label_index]

            # Skip types that don't use the field_data section:
            # - Types 0-5, 8: inline data (stored directly in data_or_offset)
            # - Type 14: Struct (data_or_offset is struct index)
            # - Type 15: List (data_or_offset is offset into list_indices section)
            if field.type in [0, 1, 2, 3, 4, 5, 8, 14, 15]:
                continue

            # Type 10 = CExoString (stored in field data section)
            if field.type == 10:
                # Check if this is the specific field we loaded into npc_data
                if label in self.npc_data and self.npc_data[label].field_index == idx:
                    # This is our field - get current value or use new value if this is the field we're updating
                    if label == field_name:
                        value = new_value
                    else:
                        value = self.npc_data[label].value

                    # Encode as CExoString format: 4 bytes length + UTF-8 string
                    string_bytes = value.encode('utf-8')
                    data = bytearray()
                    data.extend(len(string_bytes).to_bytes(4, "little"))
                    data.extend(string_bytes)

                    # Mark the ORIGINAL byte range as claimed (not the new size!)
                    # This prevents other fields from being incorrectly skipped when this field grows
                    orig_offset = self.header.field_data_offset + field.data_or_offset
                    orig_str_len = int.from_bytes(file_data[orig_offset:orig_offset+4], "little")
                    orig_size = 4 + orig_str_len
                    claimed_ranges.append((field.data_or_offset, field.data_or_offset + orig_size))

                    field_data_items.append({
                        'field_index': idx,
                        'field': field,
                        'label': label,
                        'data': data,
                        'offset': field.data_or_offset,
                        'orig_size': orig_size  # Store original size for range mapping
                    })
                else:
                    # This is a different field with the same label - preserve its original data
                    # Skip if we've already processed this offset or it's within a claimed range
                    if field.data_or_offset in processed_offsets:
                        continue
                    if is_offset_claimed(field.data_or_offset):
                        continue
                    processed_offsets.add(field.data_or_offset)

                    offset = self.header.field_data_offset + field.data_or_offset

                    # Read the size: 4 bytes for length + the string data
                    try:
                        string_len = int.from_bytes(file_data[offset:offset+4], "little")
                        size = 4 + string_len
                        data = file_data[offset:offset+size]

                        # Mark this byte range as claimed
                        claimed_ranges.append((field.data_or_offset, field.data_or_offset + size))

                        field_data_items.append({
                            'field_index': idx,
                            'field': field,
                            'label': label,
                            'data': data,
                            'offset': field.data_or_offset,
                            'orig_size': size  # Store original size for range mapping
                        })
                    except:
                        # If we can't read it, skip this field
                        continue

            # Type 12 = CExoLocString (stored in field data section)
            elif field.type == 12:
                # Check if this is the specific field we loaded into npc_data
                if label in self.npc_data and self.npc_data[label].field_index == idx and self.npc_data[label].loc_string:
                    loc_string = self.npc_data[label].loc_string

                    # If this is the field we're updating, use the new value
                    if label == field_name:
                        loc_string.set_string(new_value, language_id)

                    # For fields we're NOT editing, preserve the original total_size from file
                    # For fields we ARE editing, use the newly calculated total_size
                    preserve_size = (label != field_name)
                    data = loc_string.to_bytes(preserve_total_size=preserve_size)

                    # Mark the ORIGINAL byte range as claimed (not the new size!)
                    # CExoLocString: total_size (4 bytes) + total_size bytes of data
                    orig_offset = self.header.field_data_offset + field.data_or_offset
                    orig_total_size = int.from_bytes(file_data[orig_offset:orig_offset+4], "little")
                    orig_size = 4 + orig_total_size
                    claimed_ranges.append((field.data_or_offset, field.data_or_offset + orig_size))

                    field_data_items.append({
                        'field_index': idx,
                        'field': field,
                        'label': label,
                        'data': data,
                        'offset': field.data_or_offset,
                        'orig_size': orig_size  # Store original size for range mapping
                    })
                else:
                    # This is a different field with the same label - preserve its original data
                    # Skip if we've already processed this offset or it's within a claimed range
                    if field.data_or_offset in processed_offsets:
                        continue
                    if is_offset_claimed(field.data_or_offset):
                        continue
                    processed_offsets.add(field.data_or_offset)

                    offset = self.header.field_data_offset + field.data_or_offset

                    # CRITICAL: Copy raw bytes directly instead of decode/re-encode
                    # Re-encoding can change the size if there are invalid UTF-8 sequences
                    # (they become replacement characters which are 3 bytes in UTF-8)
                    try:
                        # Read just the total_size to determine how much data to copy
                        total_size = int.from_bytes(file_data[offset:offset+4], "little")
                        size = 4 + total_size
                        data = file_data[offset:offset+size]

                        # Mark this byte range as claimed
                        claimed_ranges.append((field.data_or_offset, field.data_or_offset + size))

                        field_data_items.append({
                            'field_index': idx,
                            'field': field,
                            'label': label,
                            'data': data,
                            'offset': field.data_or_offset,
                            'orig_size': size  # Store original size for range mapping
                        })
                    except:
                        # If we can't read it, skip this field
                        continue

            # For all other types that use field data section (6, 7, 9, 11, 13)
            # Read their data as-is from the original file
            elif field.type in [6, 7, 9, 11, 13]:
                # Skip if we've already processed this offset (multiple fields can share same data)
                if field.data_or_offset in processed_offsets:
                    continue

                # Skip if this offset falls within a byte range claimed by a type 10/12 field
                # (This handles cases where fields point into the middle of other fields' data)
                if is_offset_claimed(field.data_or_offset):
                    continue

                processed_offsets.add(field.data_or_offset)

                offset = self.header.field_data_offset + field.data_or_offset

                # Determine the size by finding the next field's offset or end of section
                # Find all offsets in this section (only types that actually use field_data)
                field_data_types = {6, 7, 9, 10, 11, 12, 13}
                all_offsets = [f.data_or_offset for f in self.fields if f.type in field_data_types]
                all_offsets_sorted = sorted(set(all_offsets))

                # Find current offset position
                current_offset = field.data_or_offset
                current_pos = all_offsets_sorted.index(current_offset)

                # Determine size
                if current_pos < len(all_offsets_sorted) - 1:
                    # Size is distance to next offset
                    size = all_offsets_sorted[current_pos + 1] - current_offset
                else:
                    # Last field - size is to end of field data section
                    size = self.header.field_data_count - current_offset

                # Read raw data from original file
                data = file_data[offset:offset+size]

                field_data_items.append({
                    'field_index': idx,
                    'field': field,
                    'label': label,
                    'data': data,
                    'offset': field.data_or_offset,
                    'orig_size': size  # Store original size for range mapping
                })

        # Sort by original offset to maintain order
        field_data_items.sort(key=lambda x: x['offset'])

        # Build new field data section
        new_field_data = bytearray()
        offset_map = {}  # Maps old offset to new offset

        for item in field_data_items:
            old_offset = item['offset']
            new_offset = len(new_field_data)
            offset_map[old_offset] = new_offset
            new_field_data.extend(item['data'])

        # NOTE: We do NOT add padding for 4-byte alignment
        # Original NWN files are sometimes aligned, sometimes not
        # Adding artificial padding breaks NWN:EE's validation

        # Build a list of (old_start, old_end, new_start) for claimed ranges
        # This helps map offsets that fall WITHIN a claimed range (not just at the start)
        # CRITICAL: Use orig_size (not len(item['data'])) to get correct old_end
        # For edited fields, item['data'] has NEW size, but old_end must be ORIGINAL end
        range_mappings = []
        for item in field_data_items:
            old_start = item['offset']
            new_start = offset_map[old_start]
            old_end = old_start + item['orig_size']  # Use ORIGINAL size, not new size!
            range_mappings.append((old_start, old_end, new_start))

        def get_new_offset(old_offset):
            """Get the new offset for any old offset, including those within ranges."""
            # First check if it's directly in offset_map
            if old_offset in offset_map:
                return offset_map[old_offset]

            # Otherwise, find which range this offset falls within
            for old_start, old_end, new_start in range_mappings:
                if old_start <= old_offset < old_end:
                    # Calculate offset within the range and apply to new position
                    offset_within_range = old_offset - old_start
                    return new_start + offset_within_range

            # Offset not found in any range - this shouldn't happen
            return old_offset

        # Update field offsets in the field table for ALL fields that use field_data offsets
        # This includes fields that share the same offset (and were skipped to avoid duplicating data)
        # Types that use field_data section offsets:
        # - Type 10: CExoString
        # - Type 11: ResRef
        # - Type 12: CExoLocString
        # Note: Type 14 (Struct) uses struct indices, Type 15 (List) uses list_indices section
        offset_types = {10, 11, 12}
        for field_idx, field in enumerate(self.fields):
            if field.type not in offset_types:
                continue

            old_offset = field.data_or_offset
            new_offset = get_new_offset(old_offset)

            if new_offset != old_offset:
                # Update in the fields array
                self.fields[field_idx].data_or_offset = new_offset

                # Write the new offset to the file data (in the field table)
                field_table_offset = self.header.field_offset + (field_idx * 12) + 8  # 12 bytes per field, offset is at byte 8
                file_data[field_table_offset:field_table_offset+4] = new_offset.to_bytes(4, "little")

        # Replace the entire field data section
        old_field_data_start = self.header.field_data_offset
        old_field_data_end = old_field_data_start + self.header.field_data_count

        # Reconstruct file: everything before field data + new field data + everything after field data
        new_file_data = (
            file_data[:old_field_data_start] +
            new_field_data +
            file_data[old_field_data_end:]
        )

        # Update header's field_data_count
        new_field_data_count = len(new_field_data)
        size_delta = new_field_data_count - self.header.field_data_count

        # Write new field_data_count to header (at offset 36 in header)
        header_field_data_count_offset = 36
        new_file_data[header_field_data_count_offset:header_field_data_count_offset+4] = new_field_data_count.to_bytes(4, "little")

        # Update all section offsets that come after field_data_offset
        # field_indices_offset and list_indices_offset need to be adjusted
        if size_delta != 0:
            # Update field_indices_offset (at offset 40 in header)
            if self.header.field_indices_offset > 0:
                new_field_indices_offset = self.header.field_indices_offset + size_delta
                new_file_data[40:44] = new_field_indices_offset.to_bytes(4, "little")

            # Update list_indices_offset (at offset 48 in header)
            if self.header.list_indices_offset > 0:
                new_list_indices_offset = self.header.list_indices_offset + size_delta
                new_file_data[48:52] = new_list_indices_offset.to_bytes(4, "little")

        # Write the modified file
        with open(self.file_name, 'wb') as f:
            f.write(new_file_data)

        # Update in-memory values
        self.header.field_data_count = new_field_data_count
        if self.header.field_indices_offset > 0:
            self.header.field_indices_offset += size_delta
        if self.header.list_indices_offset > 0:
            self.header.list_indices_offset += size_delta

        # CRITICAL: Update ALL npc_data locations, not just the edited field
        # When field_data is rebuilt, ALL offsets change, so we need to update all cached locations
        for label in self.npc_data:
            for item in field_data_items:
                if item['label'] == label and self.npc_data[label].field_index == item['field_index']:
                    new_loc = self.header.field_data_offset + offset_map[item['offset']]
                    self.npc_data[label].loc = new_loc
                    # Update the value for the field we just edited
                    if label == field_name:
                        self.npc_data[label].value = new_value
                    break

        return True

    def _save_cexostring(self, field_name, new_value):
        """Save a CExoString (type 10) field like Deity.

        CExoString format:
        - 4 bytes: string length (uint32)
        - N bytes: UTF-8 string data

        Args:
            field_name: Name of the field to update
            new_value: New string value

        Returns:
            True if successful, False otherwise
        """
        npc_data = self.npc_data[field_name]

        # Encode new value
        new_bytes_str = new_value.encode('utf-8')
        new_size = 4 + len(new_bytes_str)  # 4 bytes for length + string data

        # Read current file and get current string size
        offset = npc_data.loc
        with open(self.file_name, 'rb') as f:
            file_data = bytearray(f.read())
            # Get current string size from file
            f.seek(offset)
            old_string_len = int.from_bytes(f.read(4), "little")

        old_size = 4 + old_string_len

        # Check if sizes match
        if old_size == new_size:
            # Same size: update in place
            new_bytes = bytearray()
            new_bytes.extend(len(new_bytes_str).to_bytes(4, "little"))
            new_bytes.extend(new_bytes_str)

            file_data[offset:offset+old_size] = new_bytes

            with open(self.file_name, 'wb') as f:
                f.write(file_data)

            npc_data.value = new_value
            return True
        else:
            # Different size: rebuild field data section
            return self._rebuild_field_data_section(field_name, new_value)

    def save_string_field(self, field_name, new_value, language_id=0):
        """Save a string field (like Description, FirstName, LastName, Deity) to the BIC file.

        Args:
            field_name: Name of the field to update (e.g., 'Description', 'FirstName', 'Deity')
            new_value: New string value
            language_id: Language ID (0 for English, only used for CExoLocString fields)

        Returns:
            True if successful, False otherwise
        """
        if field_name not in self.npc_data:
            return False

        npc_data = self.npc_data[field_name]

        # Handle CExoString (type 10) fields like Deity
        if npc_data.data_type == 10:
            return self._save_cexostring(field_name, new_value)

        # Handle CExoLocString (type 12) fields
        # Check if this field has a CExoLocString
        if npc_data.loc_string is None:
            return False

        # Calculate the OLD size from the actual data structure (not the stored total_size)
        # This handles cases where tools like Moneo wrote incorrect total_size fields
        # Size = total_size field (4 bytes) + data
        # Data = string_ref (4) + string_count (4) + strings
        old_loc_string = npc_data.loc_string
        if old_loc_string.string_count == 0:
            # Empty: total_size field (4) + string_ref (4) = 8 bytes total
            old_calculated_size = 4 + 4
        else:
            # Non-empty: total_size field (4) + string_ref (4) + string_count (4) + strings
            old_calculated_size = 4 + 8  # total_size field + (string_ref + string_count)
            for lang_id, string in old_loc_string.strings.items():
                old_calculated_size += 8 + len(string.encode('utf-8'))  # lang_id + str_len + data

        # Update the string in the CExoLocString object
        npc_data.loc_string.set_string(new_value, language_id)
        new_bytes = npc_data.loc_string.to_bytes()
        new_size = len(new_bytes)

        # Check if sizes match based on ACTUAL data size
        if old_calculated_size == new_size:
            # Simple case: same size, update in place
            with open(self.file_name, 'rb') as f:
                file_data = bytearray(f.read())

            offset = npc_data.loc
            file_data[offset:offset+old_calculated_size] = new_bytes

            with open(self.file_name, 'wb') as f:
                f.write(file_data)

            npc_data.value = new_value
            return True
        else:
            # Complex case: size changed, need to rebuild field data section
            self._rebuild_field_data_section(field_name, new_value, language_id)
            return True

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

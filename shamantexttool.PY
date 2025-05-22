import struct
import re

ROM_PATH = "Shaman King - Master of Spirits (USA).gba"
DUMP_PATH = "dump.txt"

TEXT_BASE_OFFSET = 0xEE1063
POINTER_TABLE_OFFSET = 0xEE2194
POINTER_STRIDE = 4
TERMINATOR = 0xEE
FREE_SPACE_BYTE = 0xFF

def read_pointer(rom, offset):
    pointer_bytes = rom[offset:offset+3]
    return int.from_bytes(pointer_bytes, 'little')

def write_pointer(rom, offset, target_offset):
    rom[offset:offset+3] = target_offset.to_bytes(3, 'little')
    rom[offset+3] = 0x08

def extract_text(rom, offset):
    result = []
    while rom[offset] != TERMINATOR:
        result.append(rom[offset])
        offset += 1
    raw = bytes(result)
    try:
        return raw.decode("cp1252")
    except UnicodeDecodeError:
        # Replace unsupported bytes with [U+XX]
        return ''.join(
            f"[U+{b:02X}]" if b > 0xFF or chr(b) not in bytes([b]).decode("cp1252", errors="ignore") else chr(b)
            for b in raw
        )

def find_free_space(rom, size, start=0x0EF0000):
    i = start
    while i + size < len(rom):
        if all(b == FREE_SPACE_BYTE for b in rom[i:i+size]):
            return i
        i += 4
    raise RuntimeError("Không tìm thấy vùng trống phù hợp.")

def encode_text(text):
    # Replace [U+XX] with original byte
    def replace_unicode(match):
        code = int(match.group(1), 16)
        return bytes([code])

    pattern = re.compile(r"\[U\+([0-9A-Fa-f]{2})\]")
    clean_text = pattern.sub(lambda m: replace_unicode(m).decode("latin1"), text)

    return clean_text.encode("cp1252", errors="replace") + bytes([TERMINATOR])

def export_text(rom_path):
    with open(rom_path, "rb") as f:
        rom = f.read()

    out = []
    ptr_offset = POINTER_TABLE_OFFSET
    index = 0

    while ptr_offset + 4 <= len(rom) and rom[ptr_offset+3] == 0x08:
        text_offset = read_pointer(rom, ptr_offset)
        if text_offset >= len(rom):
            break
        text = extract_text(rom, text_offset)
        out.append(f"#%03d @0x{ptr_offset:X}\n{text}\n")
        ptr_offset += POINTER_STRIDE
        index += 1

    with open(DUMP_PATH, "w", encoding="cp1252", errors="replace") as f:
        f.write("\n".join(out))

    print(f"[✓] Đã xuất {index} dòng text vào {DUMP_PATH}")

def import_text(rom_path):
    with open(rom_path, "rb") as f:
        rom = bytearray(f.read())

    with open(DUMP_PATH, "r", encoding="cp1252") as f:
        lines = f.readlines()

    entries = []
    ptr_offset = None
    buffer = []

    for line in lines:
        line = line.strip()
        if line.startswith("#") and "@" in line:
            if ptr_offset is not None:
                entries.append((ptr_offset, "\n".join(buffer).strip()))
            try:
                ptr_offset = int(line.split("@")[1], 16)
            except:
                ptr_offset = None
            buffer = []
        elif ptr_offset is not None:
            buffer.append(line)

    if ptr_offset is not None:
        entries.append((ptr_offset, "\n".join(buffer).strip()))

    current_offset = 0x0EF0000

    for ptr_offset, text in entries:
        text_bytes = encode_text(text)
        dest_offset = find_free_space(rom, len(text_bytes), current_offset)
        rom[dest_offset:dest_offset+len(text_bytes)] = text_bytes
        write_pointer(rom, ptr_offset, dest_offset)
        current_offset = dest_offset + len(text_bytes)

    out_path = rom_path.replace(".gba", " [MODDED].gba")
    with open(out_path, "wb") as f:
        f.write(rom)

    print(f"[✓] Đã nhập text và lưu vào: {out_path}")

def main():
    print("GBA Text Tool (CP1252 + Pointer + [U+xx] fallback)")
    print("1. Xuất text từ ROM")
    print("2. Nhập text vào ROM")
    choice = input("Chọn (1/2): ").strip()

    path = input("Nhập đường dẫn ROM .gba: ").strip('"')

    if choice == '1':
        export_text(path)
    elif choice == '2':
        import_text(path)
    else:
        print("❌ Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()

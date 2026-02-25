"""Wire format constants."""

PACKET_MAGIC = bytes([0x42, 0x6C, 0x75, 0x65])  # {'B','l','u','e'}
PACKET_HEADER_SIZE = 8
HEADER_SIZE = 8
HEADER_FIELD_COUNT = 3  # ordinals 0..2 reserved for message header
BLUEBERRY_PORT = 16962  # 0x4242, {'B','B'}

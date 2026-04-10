"""Various XML utilities, including a pretifier.
"""

from lxml import etree


def prettify_xml_bytes(xml_bytes: bytes, encoding: str = "utf-8") -> str:
    """Parse rough XML bytes and return a prettified string (with an XML declaration)."""
    parser = etree.XMLParser(recover=True)           # tolerate malformed/rough XML
    root = etree.fromstring(xml_bytes, parser=parser)
    pretty_bytes = etree.tostring(root, encoding=encoding, xml_declaration=True, pretty_print=True, standalone=False)
    return pretty_bytes.decode(encoding)


if __name__ == '__main__':
    print(f"{__file__} - simple tests")
    raw = b"<root><child attr='1'>text<sub>more</sub></child><p>one</p></root>"
    print(prettify_xml_bytes(raw))
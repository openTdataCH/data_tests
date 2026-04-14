"""A simple "bridge" from XML to JSON, allowing to map XML-data to a (maybe incomplete) JSON or Python dict/list copy of it.

"""
from collections import defaultdict

from lxml import etree as et
from lxml.etree import _Element


def _short_ns(ns_dict: dict, s: str) -> str:
    for k in ns_dict.keys():
        s = s.replace(k, ns_dict.get(k))
    return s


def _tag_name(elem):
    # keep namespace URI if present: "{uri}local"
    return elem.tag

def _element_to_dict(elem, ns_dict):
    node = {}
    # attributes
    for k, v in elem.attrib.items():
        k_short = _short_ns(ns_dict, k)
        node[f"@{k_short}"] = v
    # children
    children = list(elem)
    if children:
        dd = defaultdict(list)
        for child in children:
            name = _short_ns(ns_dict, _tag_name(child))
            dd[name].append(_element_to_dict(child, ns_dict))
        for name, items in dd.items():
            node[_short_ns(ns_dict, name)] = items if len(items) > 1 else items[0]
    # text
    text = (elem.text or "").strip()
    if text:
        # if there are other keys, store under "#text", else set as value
        if node:
            node["#text"] = text
        else:
            return text
    return node


def prettify_xml_bytes(xml_bytes: bytes, encoding: str = "utf-8") -> str:
    """Parse rough XML bytes and return a prettified string (with an XML declaration)."""
    parser = et.XMLParser(recover=True)           # tolerate malformed/rough XML
    root = et.fromstring(xml_bytes, parser=parser)
    pretty_bytes = et.tostring(root, encoding=encoding, xml_declaration=True, pretty_print=True, standalone=False)
    return pretty_bytes.decode(encoding)


def xml_to_dict(source: object) -> dict:
    """Convert an XML source (bytes, str or lxml ElementTree) into a python dict/list representation, or a JSON"""
    if type(source) == bytes:
        root = et.fromstring(source)
    if type(source) == str:
        root = et.fromstring(source.encode('utf-8'))
    if type(source) == _Element:
        root = source
    if root is None:
        raise TypeError(f"XML source type ({type(source)}) is not supported in xml_to_dict(), must be bytes, str or lxml _Element.")

    ns_dict = {"{" + str(v) + "}": (k + ':' if k else '') for k, v in root.nsmap.items()}
    ns_dict["{http://www.w3.org/XML/1998/namespace}"] = "xml:"
    result = { _short_ns(ns_dict, _tag_name(root)): _element_to_dict(root, ns_dict) }

    return result


if __name__ == "__main__":
    print(f"{__file__} - simple tests")
    xmlbytes = b"<root><child attr='1'>text<sub>more</sub></child><p>one</p></root>"
    print(prettify_xml_bytes(xmlbytes))
    print(xml_to_dict(xmlbytes))
    print(xml_to_dict(xmlbytes.decode('utf-8')))
    print(xml_to_dict(et.fromstring(xmlbytes)))

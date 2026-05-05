"""Utility functions for string handling

"""

def strip_html_tags(text: str) -> str:
    """In a given text (str), escape all html special characters."""
    text = str(text).replace(r'<', '&lt;').replace(r'>', '&gt;').replace(r'&', '&amp;').replace(r'"', '&quot;').replace("'", "&apos;")
    return text


def flatten(text: str) -> str:
    """In a given text (str), replace line breaks (CR and LF) by spaces."""
    text = str(text).replace('\r', ' ').replace('\n', ' ')
    return text



if __name__ == '__main__':
    print("Simple tests")
    html_string = "<p>Hello, <b>world</b>!</p>"
    clean_string = strip_html_tags(html_string)
    assert clean_string == "Hello, world!"

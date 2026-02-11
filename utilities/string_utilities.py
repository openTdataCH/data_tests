"""Utility functions for string handling

"""



import re

def strip_html_tags(text):
    """Remove HTML tags from a given string."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)



if __name__ == '__main__':
    print("Simple tests")
    html_string = "<p>Hello, <b>world</b>!</p>"
    clean_string = strip_html_tags(html_string)
    assert clean_string == "Hello, world!"

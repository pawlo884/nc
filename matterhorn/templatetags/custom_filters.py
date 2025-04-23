from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    # print("Loading custom filter...")  # Sprawdź, czy się pokazuje w terminalu
    return dictionary.get(key, '')
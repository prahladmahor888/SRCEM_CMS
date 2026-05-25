from django import template
from django.forms import DateField, DateTimeField, TimeField

register = template.Library()

@register.filter
def get_attr(obj, attr_name):
    """Dynamically get an attribute from a model instance."""
    try:
        val = getattr(obj, attr_name)
        # Handle callables if needed
        if callable(val):
            return val()
        return val
    except:
        return ""

@register.filter
def is_date(field):
    return isinstance(field.field, DateField)

@register.filter
def is_datetime(field):
    return isinstance(field.field, DateTimeField)

@register.filter
def is_time(field):
    return isinstance(field.field, TimeField)

@register.filter
def is_checkbox(field):
    from django.forms import CheckboxInput
    return isinstance(field.field.widget, CheckboxInput)

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

logger = logging.getLogger(__name__)


def extract_value(element, default=None):
    """Helper method to extract values from XML elements with consistent handling"""
    if element is None:
        return default

    # Try to get text from value element using XPath
    try:
        value_nodes = element.xpath('./value/text()')
        if value_nodes and value_nodes[0]:
            return value_nodes[0].strip()
    except (AttributeError, IndexError):
        pass

    # Fall back to element's text content
    if element.text:
        return element.text.strip()

    return default


def extract_int_value(element, default=None):
    """Helper method to extract integer values with error handling"""
    value = extract_value(element, default)
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError) as e:
        logger.warning("Error converting to int: %s", e)
        return default


def extract_text_representation(element, default=None):
    """Get the text representation when both value and text are available"""
    if element is None:
        return default

    # Use XPath to get text from "text" element
    try:
        text_nodes = element.xpath('./text/text()')
        if text_nodes and text_nodes[0]:
            return text_nodes[0].strip()
    except (AttributeError, IndexError):
        pass

    return default


def extract_field(data, event_data, field_name, numeric_fields, text_fields, log=None):
    """Extract field value based on its type"""
    if field_name == 'duration':
        extract_duration(data, event_data, log)
    elif field_name in numeric_fields:
        value = extract_int_value(data)
        if value is not None:
            event_data[field_name] = value
    elif field_name in text_fields:
        text_value = extract_text_representation(data)
        if text_value is not None:
            event_data[field_name] = text_value
        else:
            event_data[field_name] = extract_value(data)
    else:
        event_data[field_name] = extract_value(data)


def extract_duration(data, event_data, log=None):
    """Extract duration value and convert to milliseconds"""
    duration_value = extract_int_value(data)
    if duration_value is not None:
        # Convert from microseconds to milliseconds
        event_data["duration_ms"] = duration_value / 1000
    else:
        event_data["duration_ms"] = None

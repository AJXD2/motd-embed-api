"""MOTD formatting code parser - converts § codes to HTML with CSS classes"""
import re
from typing import List, Tuple


# Mapping of Minecraft formatting codes to CSS classes
COLOR_CODES = {
    '0': 'mcformat-black',
    '1': 'mcformat-dark-blue',
    '2': 'mcformat-dark-green',
    '3': 'mcformat-dark-aqua',
    '4': 'mcformat-dark-red',
    '5': 'mcformat-dark-purple',
    '6': 'mcformat-gold',
    '7': 'mcformat-gray',
    '8': 'mcformat-dark-gray',
    '9': 'mcformat-blue',
    'a': 'mcformat-green',
    'b': 'mcformat-aqua',
    'c': 'mcformat-red',
    'd': 'mcformat-light-purple',
    'e': 'mcformat-yellow',
    'f': 'mcformat-white',
}

FORMAT_CODES = {
    'k': 'mcformat-obfuscated',
    'l': 'mcformat-bold',
    'm': 'mcformat-strikethrough',
    'n': 'mcformat-underline',
    'o': 'mcformat-italic',
    'r': 'mcformat-reset',
}


def parse_motd(motd_text: str) -> str:
    """
    Parse MOTD text with § formatting codes and convert to HTML.
    
    Args:
        motd_text: Raw MOTD text with § codes
        
    Returns:
        HTML string with formatted spans
    """
    if not motd_text:
        return ""
    
    # Escape HTML entities
    motd_text = (
        motd_text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )
    
    # Split by § codes while preserving them
    parts = re.split(r'(§[0-9a-fk-or])', motd_text, flags=re.IGNORECASE)
    
    html_parts = []
    current_classes = []
    
    for part in parts:
        if not part:
            continue
            
        # Check if this is a formatting code
        if part.startswith('§') and len(part) == 2:
            code = part[1].lower()
            
            # Handle reset code
            if code == 'r':
                current_classes = []
                html_parts.append(f'<span class="mcformat-code">§r</span>')
            # Handle color codes
            elif code in COLOR_CODES:
                # Reset formatting when color changes (but keep non-color formatting)
                current_classes = [c for c in current_classes if c not in COLOR_CODES.values()]
                current_classes.append(COLOR_CODES[code])
                html_parts.append(f'<span class="mcformat-code">§{part[1]}</span>')
            # Handle formatting codes
            elif code in FORMAT_CODES:
                if FORMAT_CODES[code] not in current_classes:
                    current_classes.append(FORMAT_CODES[code])
                html_parts.append(f'<span class="mcformat-code">§{part[1]}</span>')
        else:
            # Regular text - wrap with current formatting
            if current_classes:
                classes_str = ' '.join(['mcformat'] + current_classes)
                html_parts.append(f'<span class="{classes_str}">{part}</span>')
            else:
                html_parts.append(f'<span class="mcformat mcformat-reset">{part}</span>')
    
    return ''.join(html_parts)


def parse_motd_json(motd_data: dict) -> str:
    """
    Parse MOTD from JSON text component format.
    
    Args:
        motd_data: JSON text component dict
        
    Returns:
        Parsed HTML string
    """
    if isinstance(motd_data, str):
        return parse_motd(motd_data)
    
    if not isinstance(motd_data, dict):
        return ""
    
    result = []
    
    # Handle 'text' field
    if 'text' in motd_data:
        text = motd_data['text']
        if text:
            result.append(parse_motd(text))
    
    # Handle 'extra' array
    if 'extra' in motd_data:
        for item in motd_data['extra']:
            if isinstance(item, dict):
                item_text = item.get('text', '')
                if item_text:
                    result.append(parse_motd(item_text))
            elif isinstance(item, str):
                result.append(parse_motd(item))
    
    return ''.join(result)

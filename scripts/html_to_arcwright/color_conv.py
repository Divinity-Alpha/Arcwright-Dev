import re


class ColorConverter:
    """Converts CSS colors to Arcwright hex: format.
    The plugin handles sRGB->Linear conversion automatically."""

    def convert(self, css_color):
        if not css_color:
            return None
        css_color = css_color.strip()

        if css_color.startswith('#'):
            return f'hex:{css_color}'

        m = re.match(
            r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)'
            r'(?:\s*,\s*([\d.]+))?\s*\)', css_color)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            a = float(m.group(4)) if m.group(4) else 1.0
            hex_rgb = f'#{r:02X}{g:02X}{b:02X}'
            if a < 1.0:
                lr = self._to_linear(r / 255)
                lg = self._to_linear(g / 255)
                lb = self._to_linear(b / 255)
                return f'(R={lr:.4f},G={lg:.4f},B={lb:.4f},A={a:.2f})'
            return f'hex:{hex_rgb}'

        named = {
            'transparent': '(R=0.0,G=0.0,B=0.0,A=0.0)',
            'white': 'hex:#FFFFFF',
            'black': 'hex:#000000',
            'red': 'hex:#FF0000',
            'green': 'hex:#00FF00',
            'blue': 'hex:#0000FF',
        }
        if css_color.lower() in named:
            return named[css_color.lower()]

        return None

    def _to_linear(self, c):
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

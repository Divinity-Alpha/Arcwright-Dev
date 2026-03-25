import json
import os


class FontMapper:
    DEFAULT_MAP = {
        'Barlow Condensed': '/Game/UI/Fonts/F_BarlowCondensed',
        'Barlow': '/Game/UI/Fonts/F_Barlow',
        'Share Tech Mono': '/Game/UI/Fonts/F_ShareTechMono',
        'monospace': '/Game/UI/Fonts/F_ShareTechMono',
        'sans-serif': '/Game/UI/Fonts/F_Barlow',
    }
    WEIGHT_MAP = {
        '100': 'Thin', '200': 'ExtraLight', '300': 'Light',
        '400': 'Regular', 'normal': 'Regular',
        '500': 'Medium', '600': 'SemiBold', 'semibold': 'SemiBold',
        '700': 'Bold', 'bold': 'Bold',
        '800': 'ExtraBold', '900': 'Black',
    }

    def __init__(self, map_path=None):
        self.map = dict(self.DEFAULT_MAP)
        if map_path and os.path.exists(map_path):
            with open(map_path) as f:
                self.map.update(json.load(f))

    def get_family(self, css_font_family):
        if not css_font_family:
            return None
        for font in css_font_family.split(','):
            font = font.strip().strip('"\'')
            if font in self.map:
                return self.map[font]
        return None

    def get_typeface(self, css_font_weight, css_font_style=''):
        weight = str(css_font_weight).lower().strip()
        if 'italic' in css_font_style.lower():
            return 'Italic'
        return self.WEIGHT_MAP.get(weight, 'Regular')

    def register(self, css_family, ue_path):
        self.map[css_family] = ue_path

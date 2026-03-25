from bs4 import BeautifulSoup
import re


class CSSElement:
    def __init__(self, tag, classes, styles, children, text=''):
        self.tag = tag
        self.classes = classes
        self.styles = styles
        self.children = children
        self.text = text
        self.id = ''


class HTMLParser:
    def __init__(self, html_path):
        with open(html_path, encoding='utf-8') as f:
            self.content = f.read()
        self.soup = BeautifulSoup(self.content, 'html.parser')
        self.css_vars = {}
        self.css_rules = {}

    def parse(self):
        self._extract_css()
        body = self.soup.find('body')
        if not body:
            body = self.soup
        active = self.soup.find(class_='screen active') or \
                 self.soup.find(class_='screen') or body
        return self._parse_element(active)

    def _extract_css(self):
        for style_tag in self.soup.find_all('style'):
            css_text = style_tag.string or ''
            root_match = re.search(r':root\s*\{([^}]+)\}', css_text)
            if root_match:
                for line in root_match.group(1).split(';'):
                    m = re.match(r'\s*(--[\w-]+)\s*:\s*(.+)', line)
                    if m:
                        self.css_vars[m.group(1).strip()] = \
                            m.group(2).strip()
            for m in re.finditer(
                    r'([\.\w][\w\s\.\-\#\:]+?)\s*\{([^}]+)\}', css_text):
                selector = m.group(1).strip()
                props = {}
                for prop in m.group(2).split(';'):
                    if ':' in prop:
                        k, v = prop.split(':', 1)
                        props[k.strip()] = self._resolve_var(v.strip())
                self.css_rules[selector] = props

    def _resolve_var(self, value):
        def replace_var(m):
            var_name = m.group(1).strip()
            fallback = m.group(2).strip() if m.group(2) else ''
            return self.css_vars.get(var_name, fallback)
        return re.sub(r'var\((--[\w-]+)(?:,([^)]+))?\)',
                      replace_var, value)

    def _get_computed_styles(self, element):
        styles = {}
        classes = element.get('class', [])
        for cls in classes:
            rule = self.css_rules.get(f'.{cls}', {})
            styles.update(rule)
        inline = element.get('style', '')
        if inline:
            for prop in inline.split(';'):
                if ':' in prop:
                    k, v = prop.split(':', 1)
                    styles[k.strip()] = self._resolve_var(v.strip())
        return styles

    def _parse_element(self, element, depth=0):
        if not hasattr(element, 'name') or element.name is None:
            return None
        styles = self._get_computed_styles(element)
        text = ''
        children = []
        for child in element.children:
            if hasattr(child, 'name') and child.name:
                parsed = self._parse_element(child, depth + 1)
                if parsed:
                    children.append(parsed)
            elif hasattr(child, 'string') and child.string:
                t = child.string.strip()
                if t:
                    text = t
        el = CSSElement(
            tag=element.name,
            classes=element.get('class', []),
            styles=styles,
            children=children,
            text=text,
        )
        el.id = element.get('id', '')
        return el

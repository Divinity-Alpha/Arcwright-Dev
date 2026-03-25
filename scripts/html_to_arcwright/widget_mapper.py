class WidgetMapper:
    """Maps HTML elements and CSS patterns to UMG widget types."""

    def get_widget_type(self, element):
        tag = element.tag
        styles = element.styles
        classes = element.classes

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'label'):
            return 'TextBlock'
        if tag == 'button':
            return 'Button'
        if tag == 'progress':
            return 'ProgressBar'
        if any('progress' in c for c in classes) and not element.children:
            return 'ProgressBar'
        if tag == 'input':
            return 'EditableText'
        if tag == 'img':
            return 'Image'

        if tag in ('div', 'section', 'nav', 'header',
                   'footer', 'aside', 'main', 'article'):
            display = styles.get('display', 'block')
            flex_dir = styles.get('flex-direction', 'row')
            position = styles.get('position', 'static')

            if display == 'flex':
                if flex_dir == 'column':
                    return 'VerticalBox'
                return 'HorizontalBox'
            if display == 'grid':
                return 'VerticalBox'
            if position == 'absolute':
                return 'Border'
            if 'background' in styles or 'background-color' in styles:
                return 'Border'
            return 'Border'

        return 'Border'

    def needs_canvas_slot(self, element):
        return element.styles.get('position') == 'absolute'

    def is_fill_child(self, element):
        flex = element.styles.get('flex', '')
        flex_grow = element.styles.get('flex-grow', '0')
        return flex == '1' or flex_grow == '1'

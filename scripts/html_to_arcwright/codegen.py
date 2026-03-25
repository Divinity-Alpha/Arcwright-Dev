class CommandGenerator:
    def __init__(self, widget_name, destination, resolution,
                 mapper, calc, colors, fonts):
        self.widget_name = widget_name
        self.destination = destination
        self.resolution = resolution
        self.mapper = mapper
        self.calc = calc
        self.colors = colors
        self.fonts = fonts
        self.commands = []
        self._name_counter = {}
        self._id_to_name = {}

    def _cmd(self, command, **params):
        self.commands.append({'command': command, 'params': params})

    def _unique_name(self, base):
        n = self._name_counter.get(base, 0) + 1
        self._name_counter[base] = n
        return f'{base}_{n}' if n > 1 else base

    def _widget_name_for(self, element, ue_type):
        if element.id:
            name = element.id.replace('-', '_')
            self._id_to_name[element.id] = name
            return name
        classes = [c for c in element.classes
                   if c not in ('active', 'selected', 'disabled')]
        if classes:
            base = classes[0].replace('-', '_')
            prefix = {
                'TextBlock': 'Text',
                'Border': 'Border',
                'HorizontalBox': 'HBox',
                'VerticalBox': 'VBox',
                'Button': 'Btn',
                'ProgressBar': 'ProgBar',
            }.get(ue_type, 'Widget')
            return self._unique_name(f'{prefix}_{base}')
        return self._unique_name(ue_type)

    def generate(self, root_element):
        self.commands = []

        self._cmd('create_widget_blueprint',
                  name=self.widget_name,
                  path=self.destination,
                  design_width=self.resolution[0],
                  design_height=self.resolution[1])

        self._cmd('set_widget_design_size',
                  name=self.widget_name,
                  width=self.resolution[0],
                  height=self.resolution[1])

        self._cmd('add_widget_child',
                  widget_blueprint=self.widget_name,
                  parent_widget='',
                  widget_type='CanvasPanel',
                  widget_name='CanvasPanel_Root')

        for child in root_element.children:
            self._process_element(child, 'CanvasPanel_Root', is_canvas=True)

        self._cmd('save_all')

        return self.commands

    def _process_element(self, element, parent_name,
                         is_canvas=False, z_order=0):
        ue_type = self.mapper.get_widget_type(element)
        widget_name = self._widget_name_for(element, ue_type)
        styles = element.styles

        self._cmd('add_widget_child',
                  widget_blueprint=self.widget_name,
                  parent_widget=parent_name,
                  widget_type=ue_type,
                  widget_name=widget_name)

        if is_canvas and self.mapper.needs_canvas_slot(element):
            anchors = self.calc.to_anchors(styles)
            for prop, val in anchors.items():
                self._cmd('set_widget_property',
                          widget_blueprint=self.widget_name,
                          widget_name=widget_name,
                          property=prop, value=val)
            self._cmd('set_widget_property',
                      widget_blueprint=self.widget_name,
                      widget_name=widget_name,
                      property='Slot.ZOrder', value=str(z_order))

        if not is_canvas and self.mapper.is_fill_child(element):
            self._cmd('set_widget_property',
                      widget_blueprint=self.widget_name,
                      widget_name=widget_name,
                      property='Slot.FillWidth', value='1.0')

        self._apply_styles(widget_name, ue_type, styles, element)

        if ue_type == 'TextBlock' and element.text:
            self._cmd('set_widget_property',
                      widget_blueprint=self.widget_name,
                      widget_name=widget_name,
                      property='Text', value=element.text)

        for i, child in enumerate(element.children):
            self._process_element(child, widget_name,
                                  is_canvas=False, z_order=i)

    def _apply_styles(self, widget_name, ue_type, styles, element):
        def sp(prop, val):
            self.commands.append({
                'command': 'set_widget_property',
                'params': {
                    'widget_blueprint': self.widget_name,
                    'widget_name': widget_name,
                    'property': prop,
                    'value': str(val),
                }
            })

        if ue_type == 'Border':
            bg = styles.get('background-color') or styles.get('background', '')
            if bg and bg != 'none':
                color = self.colors.convert(bg)
                if color:
                    sp('BrushColor', color)
                    sp('Brush.DrawType', 'Box')

            pad = styles.get('padding')
            if pad:
                ue_pad = self.calc.parse_padding(pad)
                if ue_pad:
                    sp('Padding', ue_pad)

            sp('HAlign', 'Fill')
            sp('VAlign', 'Fill')

        if ue_type == 'TextBlock':
            color = styles.get('color')
            if color:
                ue_color = self.colors.convert(color)
                if ue_color:
                    sp('ColorAndOpacity', ue_color)

            family = self.fonts.get_family(styles.get('font-family', ''))
            if family:
                sp('Font.Family', family)

            weight = styles.get('font-weight', '400')
            style = styles.get('font-style', '')
            typeface = self.fonts.get_typeface(weight, style)
            sp('Font.Typeface', typeface)

            size = styles.get('font-size', '')
            if size:
                px_val = self.calc.px(size)
                if px_val > 0:
                    sp('Font.Size', str(int(px_val)))

            spacing = styles.get('letter-spacing', '')
            if spacing:
                sp_val = self.calc.px(spacing)
                if sp_val:
                    sp('Font.LetterSpacing', str(int(sp_val)))

            align = styles.get('text-align', '')
            if align == 'center':
                sp('Justification', 'Center')
            elif align == 'right':
                sp('Justification', 'Right')

        opacity = styles.get('opacity', '')
        if opacity and opacity != '1':
            sp('RenderOpacity', opacity)

        if ue_type == 'ProgressBar':
            bg = styles.get('background-color', '')
            if bg:
                color = self.colors.convert(bg)
                if color:
                    sp('FillColorAndOpacity', color)

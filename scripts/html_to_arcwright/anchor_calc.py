import re


class AnchorCalc:
    def __init__(self, canvas_w=1920, canvas_h=1080):
        self.w = canvas_w
        self.h = canvas_h

    def px(self, value_str, axis_size=None):
        if not value_str:
            return 0.0
        v = str(value_str).replace('px', '').strip()
        try:
            return float(v)
        except ValueError:
            return 0.0

    def to_anchors(self, styles):
        left = self.px(styles.get('left', '0'))
        top = self.px(styles.get('top', '0'))
        w = self.px(styles.get('width', str(self.w)))
        h = self.px(styles.get('height', str(self.h)))

        fills_right = (left + w) >= self.w * 0.98
        fills_bottom = (top + h) >= self.h * 0.98

        anchor_min_x = left / self.w
        anchor_min_y = top / self.h

        anchor_max_x = 1.0 if fills_right else (left + w) / self.w
        anchor_max_y = 1.0 if fills_bottom else (top + h) / self.h

        is_stretch_x = anchor_max_x > anchor_min_x + 0.01
        is_stretch_y = anchor_max_y > anchor_min_y + 0.01

        result = {
            'Slot.Anchors.Min.X': f'{anchor_min_x:.4f}',
            'Slot.Anchors.Min.Y': f'{anchor_min_y:.4f}',
            'Slot.Anchors.Max.X': f'{anchor_max_x:.4f}',
            'Slot.Anchors.Max.Y': f'{anchor_max_y:.4f}',
        }

        if is_stretch_x and is_stretch_y:
            result['Slot.Position.X'] = '0'
            result['Slot.Position.Y'] = '0'
            result['Slot.Size.X'] = '0'
            result['Slot.Size.Y'] = '0'
        else:
            result['Slot.Position.X'] = str(left)
            result['Slot.Position.Y'] = str(top)
            result['Slot.Size.X'] = str(w)
            result['Slot.Size.Y'] = str(h)

        return result

    def parse_padding(self, padding_str):
        if not padding_str:
            return None
        parts = [self.px(p) for p in padding_str.split()]
        if len(parts) == 1:
            v = parts[0]
            return f'(Left={v},Top={v},Right={v},Bottom={v})'
        elif len(parts) == 2:
            return f'(Left={parts[1]},Top={parts[0]},' \
                   f'Right={parts[1]},Bottom={parts[0]})'
        elif len(parts) == 4:
            return f'(Left={parts[3]},Top={parts[0]},' \
                   f'Right={parts[1]},Bottom={parts[2]})'
        return None

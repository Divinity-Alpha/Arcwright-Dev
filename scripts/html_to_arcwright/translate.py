#!/usr/bin/env python3
"""HTML to Arcwright UI Translator — main entry point."""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import HTMLParser
from widget_mapper import WidgetMapper
from anchor_calc import AnchorCalc
from color_conv import ColorConverter
from font_mapper import FontMapper
from codegen import CommandGenerator


def translate(html_file, widget_name, destination,
              resolution=(1920, 1080), execute=False,
              font_map_path=None):
    """Translate an HTML/CSS UI design into Arcwright TCP commands."""
    parser = HTMLParser(html_file)
    tree = parser.parse()

    mapper = WidgetMapper()
    calc = AnchorCalc(resolution[0], resolution[1])
    colors = ColorConverter()
    fonts = FontMapper(font_map_path)

    gen = CommandGenerator(
        widget_name=widget_name,
        destination=destination,
        resolution=resolution,
        mapper=mapper,
        calc=calc,
        colors=colors,
        fonts=fonts,
    )

    commands = gen.generate(tree)

    if execute:
        from tcp_client import TCPClient
        client = TCPClient()
        failed = []
        for cmd in commands:
            r = client.send(cmd['command'], cmd['params'])
            if r.get('status') != 'ok':
                failed.append(f"{cmd['command']}: {r.get('error', '?')}")
        print(f"Executed {len(commands)} commands")
        if failed:
            print(f"Failed ({len(failed)}):")
            for f in failed:
                print(f"  {f}")

    return commands


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Translate HTML UI design to Arcwright UMG widget'
    )
    ap.add_argument('--html', required=True)
    ap.add_argument('--widget', required=True)
    ap.add_argument('--path', default='/Game/UI')
    ap.add_argument('--resolution', default='1920x1080')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--font-map', default=None)
    ap.add_argument('--output', default=None,
                    help='Save commands to JSON file')
    args = ap.parse_args()

    w, h = map(int, args.resolution.split('x'))
    commands = translate(
        html_file=args.html,
        widget_name=args.widget,
        destination=args.path,
        resolution=(w, h),
        execute=args.execute,
        font_map_path=args.font_map,
    )

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(commands, f, indent=2)
        print(f"Commands saved to {args.output}")
    else:
        print(f"Generated {len(commands)} commands")
        for cmd in commands[:5]:
            print(f"  {cmd['command']}: {list(cmd['params'].keys())}")
        if len(commands) > 5:
            print(f"  ... and {len(commands) - 5} more")

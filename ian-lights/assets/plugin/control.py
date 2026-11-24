#!/usr/bin/python3
"""Ian's fixed RAM/ring/centre controls; status and presets require no hardware I/O."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import copy, fcntl, json, re, subprocess, time, uuid
sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
STATE = Path.home() / '.local/state/ovrin-rgb'
KEYS = ('ram', 'ring', 'inner')
LABELS = ('RAM sticks', 'Light rings', 'Inner lights')
DEFAULT = {'version': 2, 'colors': dict.fromkeys(KEYS, '#ffffff'), 'presets': []}

def valid_color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError('Choose a valid color.')
    return value.lower()

def valid_colors(value):
    if not isinstance(value, dict) or set(value) != set(KEYS):
        raise ValueError('The preset must contain all three lights.')
    return {key: valid_color(value[key]) for key in KEYS}

def read_state():
    path = STATE / 'lights.json'
    state = json.loads(path.read_text()) if path.exists() else copy.deepcopy(DEFAULT)
    state['colors'] = valid_colors(state['colors'])
    return state

def save(state):
    path = STATE / 'lights.json.tmp'
    path.write_text(json.dumps(state, indent=2) + '\n')
    path.replace(STATE / 'lights.json')

def connect():
    try:
        return OpenRGBClient(name='Ian lights', protocol_version=4)
    except (ConnectionRefusedError, OSError):
        subprocess.run(['systemctl', '--user', 'start', 'ovrin-rgb.service'], check=True, capture_output=True, timeout=15)
    for _ in range(30):
        try:
            return OpenRGBClient(name='Ian lights', protocol_version=4)
        except (ConnectionRefusedError, OSError):
            time.sleep(.5)
    raise RuntimeError('Lighting service is unavailable. Try again in a moment.')

def apply(colors, selected=KEYS):
    # The wiring file is fixed during installation, never discovered by the widget.
    client = connect()
    try:
        for _ in range(20):
            ram_ready = 'ram' not in selected or sum(d.name == 'Corsair Vengeance RGB DDR5' for d in client.devices) == 2
            fan_ready = not any(key in selected for key in ('ring', 'inner')) or any(d.name == 'ASRock X870E Taichi Lite' for d in client.devices)
            if ram_ready and fan_ready:
                break
            time.sleep(.5)
            client.update()
        if 'ram' in selected:
            sticks = [d for d in client.devices if d.name == 'Corsair Vengeance RGB DDR5']
            if len(sticks) != 2:
                raise RuntimeError('The two RAM sticks are unavailable. Try again in a moment.')
            for stick in sticks:
                stick.set_mode('Direct')
                stick.set_colors([RGBColor.fromHEX(colors['ram'])] * 10)
        fan_keys = [key for key in ('ring', 'inner') if key in selected]
        if fan_keys:
            wiring = json.loads(Path(__file__).with_name('wiring.json').read_text())
            board = next((d for d in client.devices if d.name == 'ASRock X870E Taichi Lite'), None)
            if board is None:
                raise RuntimeError('Fan lighting is unavailable. Try again in a moment.')
            # Preserve all unrelated headers and pixels, including the other fan channel.
            buffer = list(board.colors)
            for key in fan_keys:
                for span in wiring[key]:
                    zone = board.zones[span['zone']]
                    offset = sum(len(z.leds) for z in board.zones[:span['zone']])
                    start, end = span['start'], span['end']
                    if not 0 <= start < end <= len(zone.leds):
                        raise RuntimeError('Fan wiring no longer matches this system.')
                    color = RGBColor.fromHEX(colors[key])
                    if wiring.get('swap_rg'):
                        color = RGBColor(color.green, color.red, color.blue)
                    buffer[offset + start:offset + end] = [color] * (end - start)
            board.set_mode('Direct')
            time.sleep(.1)
            board.set_colors(buffer)
    finally:
        client.disconnect()

def run(request):
    state = read_state()
    action = request.get('action', 'status')
    if action == 'color':
        key = request.get('light')
        if key not in KEYS:
            raise ValueError('Unknown light.')
        colors = dict(state['colors'])
        colors[key] = valid_color(request.get('color'))
        apply(colors, (key,))
        state['colors'] = colors
        save(state)
    elif action == 'save-preset':
        name = str(request.get('name', '')).strip()
        if not name or len(name) > 40:
            raise ValueError('Enter a preset name of 1–40 characters.')
        if any(p['name'].casefold() == name.casefold() for p in state['presets']):
            raise ValueError('That name is already saved. Choose another name.')
        state['presets'].append({'id': uuid.uuid4().hex, 'name': name, 'colors': dict(state['colors'])})
        save(state)
    elif action in ('load-preset', 'delete-preset'):
        preset = next((p for p in state['presets'] if p['id'] == request.get('id')), None)
        if preset is None:
            raise ValueError('That preset no longer exists.')
        if action == 'load-preset':
            colors = valid_colors(preset['colors'])
            apply(colors)
            state['colors'] = colors
        else:
            state['presets'].remove(preset)
        save(state)
    elif action == 'restore':
        apply(state['colors'])
    elif action == 'prepare-sleep':
        # Release device handles before sleep. Off/Static mode changes failed
        # long-suspend tests and are deliberately omitted.
        subprocess.run(['systemctl', '--user', 'stop', 'ovrin-rgb.service'],
                       check=True, capture_output=True, timeout=2)
    elif action != 'status':
        raise ValueError('Unknown action.')
    return {'ok': True, 'lights': [{'key': key, 'name': label, 'color': state['colors'][key]} for key, label in zip(KEYS, LABELS)], 'presets': state['presets']}

def main():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'control.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            result = run(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {})
        except Exception as error:
            result = {'ok': False, 'error': str(error)}
        print(json.dumps(result), flush=True)
        return 0 if result['ok'] else 1
if __name__ == '__main__':
    sys.exit(main())

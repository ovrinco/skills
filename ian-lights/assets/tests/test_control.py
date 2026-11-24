import importlib.util, pathlib, sys, tempfile, unittest, copy
from unittest.mock import patch
PLUGIN=pathlib.Path(__file__).resolve().parents[1]/'plugin'
sys.path.insert(0, str(pathlib.Path(str(PLUGIN/'vendor')).resolve()))
spec=importlib.util.spec_from_file_location('lights', str(PLUGIN/'control.py'))
lights=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lights)

class Presets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=lights.STATE
        lights.STATE=pathlib.Path(self.tmp.name)
    def tearDown(self):
        lights.STATE=self.old
        self.tmp.cleanup()
    def test_status_and_presets_do_not_connect(self):
        with patch.object(lights, 'connect', side_effect=AssertionError('No discovery expected')):
            self.assertEqual(len(lights.run({})['lights']),3)
            r=lights.run({'action':'save-preset','name':'Evening'})
            saved=r['presets'][0]
            self.assertEqual(saved['colors'],dict.fromkeys(lights.KEYS,'#ffffff'))
            r=lights.run({'action':'delete-preset','id':saved['id']})
            self.assertEqual(r['presets'],[])
    def test_load_restores_all_three_saved_colors(self):
        with patch.object(lights,'apply') as send:
            lights.run({'action':'color','light':'ring','color':'#123456'})
            r=lights.run({'action':'save-preset','name':'Evening'})
            lights.run({'action':'color','light':'ring','color':'#abcdef'})
            r=lights.run({'action':'load-preset','id':r['presets'][0]['id']})
            self.assertEqual(r['lights'][1]['color'],'#123456')
            send.assert_called_with({'ram':'#ffffff','ring':'#123456','inner':'#ffffff'})
    def test_failed_write_preserves_saved_colors(self):
        with patch.object(lights,'apply',side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):
                lights.run({'action':'color','light':'ram','color':'#123456'})
        self.assertEqual(lights.read_state()['colors'],lights.DEFAULT['colors'])
    def test_duplicate_name_and_invalid_color_rejected(self):
        lights.run({'action':'save-preset','name':'Evening'})
        with self.assertRaises(ValueError):
            lights.run({'action':'save-preset','name':'evening'})
        with patch.object(lights,'apply') as send:
            for value in ['red','#123','../foo',None]:
                with self.assertRaises(ValueError):
                    lights.run({'action':'color','light':'ring','color':value})
            send.assert_not_called()
    def test_deleting_one_preset_preserves_others_and_current_colors(self):
        first=lights.run({'action':'save-preset','name':'A'})['presets'][0]
        lights.run({'action':'save-preset','name':'B'})
        with patch.object(lights,'apply') as send:
            result=lights.run({'action':'delete-preset','id':first['id']})
            send.assert_not_called()
        self.assertEqual([p['name'] for p in result['presets']],['B'])
        self.assertEqual(lights.read_state()['colors'],lights.DEFAULT['colors'])


class HardwareRouting(unittest.TestCase):
    def test_prepare_sleep_stops_backend_without_hardware_or_state_writes(self):
        with patch.object(lights,'connect') as connect, patch.object(lights,'read_state',return_value=copy.deepcopy(lights.DEFAULT)), patch.object(lights,'save') as save, patch.object(lights.subprocess,'run') as stop:
            lights.run({'action':'prepare-sleep'})
            connect.assert_not_called()
            save.assert_not_called()
            stop.assert_called_once_with(['systemctl','--user','stop','ovrin-rgb.service'],check=True,capture_output=True,timeout=2)

    def make_client(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from openrgb.utils import RGBColor
        board=SimpleNamespace(name='ASRock X870E Taichi Lite', colors=[RGBColor(255,255,255)]*241,
            zones=[SimpleNamespace(leds=[None]*n) for n in (1,80,80,80)], set_mode=Mock(), set_colors=Mock())
        ram=[SimpleNamespace(name='Corsair Vengeance RGB DDR5',set_mode=Mock(),set_colors=Mock()) for _ in range(2)]
        client=SimpleNamespace(devices=ram+[board],disconnect=Mock())
        return client,board,ram
    def test_ring_write_preserves_inner_and_unrelated_headers(self):
        client,board,ram=self.make_client()
        with patch.object(lights,'connect',return_value=client),patch.object(lights.time,'sleep'):
            lights.apply({'ram':'#123456','ring':'#aa5522','inner':'#654321'},('ring',))
        colors=board.set_colors.call_args.args[0]
        for index,color in enumerate(colors):
            expected=(85,170,34) if 89 <= index < 109 else (255,255,255)
            self.assertEqual((color.red,color.green,color.blue),expected)
        for stick in ram:stick.set_colors.assert_not_called()
        client.disconnect.assert_called_once()
    def test_ram_write_uses_direct_without_touching_fans(self):
        client,board,ram=self.make_client()
        with patch.object(lights,'connect',return_value=client):
            lights.apply({'ram':'#123456','ring':'#aa5522','inner':'#654321'},('ram',))
        for stick in ram:
            stick.set_mode.assert_called_once_with('Direct')
            colors=stick.set_colors.call_args.args[0]
            self.assertEqual(len(colors),10)
            self.assertTrue(all((c.red,c.green,c.blue)==(18,52,86) for c in colors))
        board.set_colors.assert_not_called()

if __name__=='__main__':unittest.main()

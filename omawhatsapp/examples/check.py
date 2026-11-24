"""Inspect real guards with invented requests; forbid subprocess/network operations."""
from pathlib import Path
import importlib.util,sys,unittest
from unittest.mock import patch
runtime=Path(__file__).resolve().parents[1]/'runtime'
sys.path.insert(0,str(runtime))
spec=importlib.util.spec_from_file_location('oma_release_bridge',runtime/'omawhatsapp.py')
bridge=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bridge;spec.loader.exec_module(bridge)
class Guards(unittest.TestCase):
    def test_classified_registry(self):
        backend=bridge.Backend.__new__(bridge.Backend)
        with patch.object(bridge.subprocess,'run',side_effect=AssertionError('External invocation forbidden')):
            result=backend.capabilities()
        self.assertEqual(result['wacli_parity_version'],'0.17.1')
        self.assertGreater(result['operation_count'],0)
    def test_unknown_and_global_args_refused(self):
        with self.assertRaises(bridge.OmaWhatsAppError):bridge.Backend._transport_path(['future-command'])
        with self.assertRaises(bridge.OmaWhatsAppError):bridge.Backend._transport_args(['--json','messages','list'])
        with self.assertRaises(bridge.OmaWhatsAppError):bridge.Backend._transport_args(['messages',None])
    def test_unauthorized_mutation_refused_before_transport(self):
        operation=next(path for path,policy in bridge.WACLI_OPERATION_POLICIES.items() if policy=='whatsapp-write')
        backend=bridge.Backend.__new__(bridge.Backend)
        with patch.object(bridge.subprocess,'run',side_effect=AssertionError('External invocation forbidden')):
            with self.assertRaises(bridge.OmaWhatsAppError):backend.transport({'args':list(operation)})
if __name__=='__main__':unittest.main()

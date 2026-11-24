import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('backup',Path(__file__).with_name('project_backup.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BackupTests(unittest.TestCase):
 def test_oversize_rejected_without_copy(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'data').write_bytes(b'x'*32)
   with self.assertRaises(ValueError):b.inventory({'source':str(p)},max_bytes=16)
   self.assertEqual(sorted(x.name for x in p.iterdir()),['data'])
 def test_generated_trees_excluded_and_symlinks_not_followed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'target').mkdir();(p/'target'/'huge').write_bytes(b'x'*100)
   (p/'source').write_text('keep');(p/'link').symlink_to('/etc')
   plan=b.inventory({'project':str(p)})
   self.assertEqual(plan['total_bytes'],4)
   self.assertEqual(len(plan['files']),2)
 def test_overlapping_roots_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'child').mkdir()
   with self.assertRaises(ValueError):b.inventory({'a':str(p),'b':str(p/'child')})
 def test_roundtrip_and_no_staging(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);src=p/'source';src.mkdir();(src/'file').write_text('preserved')
   plan=b.inventory({'source':str(src)})
   receipt=b.create(plan,p/'out','test')
   self.assertEqual(receipt['files_verified'],1)
   self.assertEqual(sorted(x.name for x in (p/'out').iterdir()),['MANIFEST.json','README.md','SHA256SUMS','VERIFICATION.json','test-checkpoint.tar.gz'])
 def test_shared_data_separation_and_reference(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);data=p/'data';data.mkdir();(data/'record').write_text('shared')
   archive=p/'baseline.tgz';archive.write_bytes(b'baseline');manifest=p/'manifest.json';manifest.write_text('{}')
   shared={'archive':str(archive),'archive_sha256':b.sha(archive),'manifest':str(manifest),'manifest_sha256':b.sha(manifest),'protected_roots':[str(data)]}
   alias=p/'alias';alias.symlink_to(data)
   for root in [data,p,alias]:
    with self.assertRaisesRegex(ValueError,'overlaps shared data'):b.inventory({'source':str(root)},shared_data=shared)
   src=p/'app';src.mkdir();(src/'main').write_text('code')
   plan=b.inventory({'app':str(src)},shared_data=shared);b.create(plan,p/'out','version')
   import json
   saved=json.loads((p/'out/MANIFEST.json').read_text());self.assertEqual(saved['shared_data'],shared);self.assertEqual(list(saved['sha256']),['app/main'])
   archive.write_bytes(b'corrupt')
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):b.inventory({'app':str(src)},shared_data=shared)
 def test_changed_plan_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);src=p/'source';src.mkdir();f=src/'file';f.write_text('old')
   plan=b.inventory({'source':str(src)});f.write_text('changed')
   with self.assertRaises(ValueError):b.create(plan,p/'out','test')
   self.assertFalse((p/'out').exists())
if __name__=='__main__':unittest.main()

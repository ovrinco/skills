"""Create and restore only an invented checkpoint in a fresh temporary directory."""
from pathlib import Path
import importlib.util,tarfile,tempfile,hashlib
script=Path(__file__).resolve().parents[1]/'scripts/project_backup.py'
spec=importlib.util.spec_from_file_location('bounded_backup',script)
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)
with tempfile.TemporaryDirectory(prefix='atlas-backup-') as tmp:
    root=Path(tmp);source=root/'project';source.mkdir()
    (source/'main.txt').write_text('preserved')
    (source/'target').mkdir();(source/'target/cache.bin').write_bytes(b'generated')
    (source/'source-link').symlink_to('main.txt')
    plan=backup.inventory({'application':str(source)})
    output=root/'checkpoint';receipt=backup.create(plan,output,'atlas')
    archive=output/'atlas-checkpoint.tar.gz'
    expected=(output/'SHA256SUMS').read_text().split()[0]
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
    restored=root/'restored';restored.mkdir()
    with tarfile.open(archive,'r:gz') as content:content.extractall(restored,filter='data')
    app=restored/'atlas-checkpoint/application'
    assert (app/'main.txt').read_text()=='preserved'
    assert (app/'source-link').is_symlink() and (app/'source-link').read_text()=='preserved'
    assert not (app/'target').exists()
    (source/'large.txt').write_bytes(b'x'*32)
    try:backup.inventory({'application':str(source)},max_bytes=16)
    except ValueError:pass
    else:raise AssertionError('Input cap must refuse the plan')
    assert (source/'main.txt').read_text()=='preserved'
    print('Source checkpoint, symlink, generated exclusion, verified hash, clean restore and early size rejection passed.')

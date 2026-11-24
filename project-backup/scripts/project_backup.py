"""Lightweight, bounded, streaming project backups. Plan first; never stage a tree."""
import argparse, gzip, hashlib, io, json, os, re, tarfile
from pathlib import Path

MAX_INPUT=4*1024**3
MAX_ARCHIVE=2*1024**3
MAX_FILES=100000
EXCLUDED={'.git','target','node_modules','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.cache','.next','.nuxt','.zig-cache','zig-cache','_build','deps'}

def safe_name(name):
 p=Path(name)
 if not name or p.is_absolute() or '..' in p.parts or str(p)=='.':raise ValueError('Unsafe archive name: '+name)
 return name

def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def signature(path):
 s=path.lstat();return [s.st_size,s.st_mtime_ns,s.st_mode,s.st_ino,s.st_dev]

def inventory(sources,max_bytes=MAX_INPUT,shared_data=None):
 if max_bytes>MAX_INPUT:raise ValueError('Input cap cannot be raised implicitly')
 if shared_data:
  for key in ['archive','manifest']:
   if sha(Path(shared_data[key]))!=shared_data[key+'_sha256']:raise ValueError('Shared data '+key+' checksum mismatch')
  if not shared_data.get('protected_roots'):raise ValueError('Shared data needs protected roots')
 roots=[];files=[];excluded=[];total=0;summary={}
 for name,cfg in sources.items():
  safe_name(name)
  if isinstance(cfg,str):cfg={'path':cfg}
  root=Path(cfg['path']).expanduser().absolute()
  if cfg.get('resolve'):root=root.resolve()
  if shared_data:
   for protected in shared_data['protected_roots']:
    q=Path(protected).expanduser().resolve();r=root.resolve()
    if r==q or r.is_relative_to(q) or q.is_relative_to(r):raise ValueError('Version backup overlaps shared data: '+str(root))
  if not root.exists() and not root.is_symlink():raise ValueError('Missing source: '+str(root))
  for other in roots:
   if root==other or root.is_relative_to(other) or other.is_relative_to(root):raise ValueError('Overlapping source roots')
  roots.append(root)
  local_excludes=cfg.get('exclude',[]);count=0;size=0
  def visit(p,rel):
   nonlocal total,count,size
   if rel.parts and (any(x in EXCLUDED or x.endswith('-cargo-home') or x.endswith('-target') for x in rel.parts) or any(rel==Path(x) or rel.is_relative_to(Path(x)) for x in local_excludes)):
    excluded.append(str(p));return
   if p.is_symlink():kind='symlink'
   elif p.is_dir():
    for child in sorted(p.iterdir()):visit(child,rel/child.name)
    return
   elif p.is_file():kind='file'
   else:raise ValueError('Special/live transient file must be explicitly excluded: '+str(p))
   dest=str(Path(name)/rel);safe_name(dest)
   item={'path':str(p),'name':dest,'kind':kind,'signature':signature(p)}
   if kind=='symlink':item['target']=os.readlink(p)
   else:
    total+=item['signature'][0];size+=item['signature'][0]
    if total>max_bytes:raise ValueError('Input exceeds lightweight cap; narrow scope before copying')
   files.append(item);count+=1
   if len(files)>MAX_FILES:raise ValueError('Too many files; likely duplicated workspaces or dependencies')
  visit(root,Path())
  summary[name]={'path':str(root),'files':count,'bytes':size}
 names=[x['name'] for x in files]
 if len(names)!=len(set(names)):raise ValueError('Duplicate archive paths')
 plan={'format':2,'sources':sources,'files':files,'excluded':excluded,'summary':summary,'total_bytes':total,'max_archive_bytes':MAX_ARCHIVE}
 if shared_data:plan['shared_data']=shared_data
 return plan

class BoundedWriter:
 def __init__(self,file,limit):self.file=file;self.limit=limit;self.count=0
 def write(self,data):
  if self.count+len(data)>self.limit:raise ValueError('Compressed archive exceeded cap; no verified backup created')
  result=self.file.write(data);self.count+=result;return result
 def flush(self):return self.file.flush()

def create(plan,base,name):
 os.umask(0o077)
 if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',name):raise ValueError('Invalid project name')
 fresh=inventory(plan['sources'],shared_data=plan.get('shared_data'))
 if fresh!=plan:raise ValueError('Source inventory changed since plan; create and review a new plan')
 base=Path(base).absolute()
 for item in plan['sources'].values():
  p=Path(item if isinstance(item,str) else item['path']).expanduser().resolve()
  if base.resolve()==p or base.resolve().is_relative_to(p):raise ValueError('Archive cannot be inside a source')
 if base.exists():raise FileExistsError('Refusing to reuse existing output directory')
 base.mkdir(parents=True,mode=0o700)
 archive=base/(name+'-checkpoint.tar.gz');partial=archive.with_suffix('.gz.partial');prefix=name+'-checkpoint/'
 manifest={'sources':plan['sources'],'excluded':plan['excluded'],'sha256':{},'symlinks':{},'source_stability':'all selected source bytes verified again after archive creation'}
 restore='Extract into a NEW empty directory. Verify SHA256SUMS and MANIFEST.json. Sources and exclusions are recorded in the manifest. Do not replace newer live state or restore test data over live data. Rebuild excluded generated dependencies from retained manifests/lockfiles.\n'
 if plan.get('shared_data'):
  manifest['shared_data']=plan['shared_data']
  restore+='This is a version-only checkpoint. Shared data is not included. Its separate baseline, checksum, date and limitations are recorded in MANIFEST.json shared_data. Retain current live data when restoring an app version; do not automatically roll data back to that baseline.\n'
 with partial.open('xb') as raw:
  with gzip.GzipFile(fileobj=BoundedWriter(raw,MAX_ARCHIVE),mode='wb',compresslevel=6,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w|',dereference=False) as tar:
    for item in plan['files']:
     p=Path(item['path']);rel=item['name']
     if signature(p)!=item['signature']:raise ValueError('Source changed: '+str(p))
     if item['kind']=='file':manifest['sha256'][rel]=sha(p)
     else:manifest['symlinks'][rel]=os.readlink(p)
     tar.add(p,arcname=prefix+rel,recursive=False)
     if signature(p)!=item['signature']:raise ValueError('Source changed while archiving: '+str(p))
    for rel,body in [('MANIFEST.json',json.dumps(manifest,indent=2)),('RESTORE.md',restore)]:
     data=body.encode();info=tarfile.TarInfo(prefix+rel);info.size=len(data);info.mode=0o600;tar.addfile(info,io.BytesIO(data))
 verified={};links={}
 with tarfile.open(partial,'r|gz') as tar:
  for item in tar:
   rel=item.name.removeprefix(prefix)
   if item.issym():links[rel]=item.linkname
   elif item.isfile():
    with tar.extractfile(item) as f:verified[rel]=hashlib.file_digest(f,'sha256').hexdigest()
   elif item.islnk():verified[rel]=verified[item.linkname.removeprefix(prefix)]
 for rel,h in manifest['sha256'].items():
  if verified.get(rel)!=h:raise ValueError('Archive verification failed: '+rel)
 if links!=manifest['symlinks']:raise ValueError('Symlink verification failed')
 for item in plan['files']:
  p=Path(item['path'])
  if signature(p)!=item['signature']:raise ValueError('Source changed over backup interval: '+str(p))
  if item['kind']=='file' and sha(p)!=manifest['sha256'][item['name']]:raise ValueError('Source content changed: '+str(p))
  if item['kind']=='symlink' and os.readlink(p)!=item['target']:raise ValueError('Source link changed')
 if inventory(plan['sources'],shared_data=plan.get('shared_data'))!=plan:raise ValueError('Source paths changed over backup interval')
 partial.rename(archive);digest=sha(archive)
 (base/'MANIFEST.json').write_text(json.dumps(manifest,indent=2));(base/'README.md').write_text(restore);(base/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
 receipt={'status':'VERIFIED','directory':str(base),'archive':str(archive),'bytes':archive.stat().st_size,'files_verified':len(manifest['sha256']),'symlinks_verified':len(links),'sha256':digest}
 (base/'VERIFICATION.json').write_text(json.dumps(receipt,indent=2));return receipt

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='cmd',required=True)
 p=sub.add_parser('plan');p.add_argument('--sources',required=True);p.add_argument('--out',required=True)
 p.add_argument('--shared-data',help='Shared baseline descriptor; rejects source overlap with its protected data roots')
 p=sub.add_parser('create');p.add_argument('--plan',required=True);p.add_argument('--base-dir',required=True);p.add_argument('--name',required=True)
 a=ap.parse_args();os.umask(0o077)
 if a.cmd=='plan':
  shared=json.loads(Path(a.shared_data).read_text()) if a.shared_data else None
  plan=inventory(json.loads(Path(a.sources).read_text()),shared_data=shared);Path(a.out).write_text(json.dumps(plan,indent=2));print(json.dumps({'summary':plan['summary'],'total_bytes':plan['total_bytes'],'file_count':len(plan['files']),'excluded_count':len(plan['excluded']),'max_archive_bytes':MAX_ARCHIVE},indent=2))
 else:print(json.dumps(create(json.loads(Path(a.plan).read_text()),Path(a.base_dir),a.name),indent=2))
if __name__=='__main__':main()

"""Exercise actual XLSX tools against an invented standards-shaped workbook."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import xml.etree.ElementTree as ET
scripts=Path(__file__).resolve().parents[1]/'scripts'
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
def fixture(path,formula=False):
    rows=[]
    for i,(a,b) in enumerate([('name','value'),('alpha','1'),('beta','2')],1):
        cells=f'<c r="A{i}" t="inlineStr"><is><t>{a}</t></is></c><c r="B{i}" t="inlineStr"><is><t>{b}</t></is></c>'
        if formula and i==2:cells+='<c r="C2"><f t="shared">1+1</f><v>2</v></c>'
        rows.append(f'<row r="{i}">{cells}</row>')
    files={
    '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/></Types>',
    '_rels/.rels':f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
    'xl/workbook.xml':f'<workbook xmlns="{NS}" xmlns:r="{R}"><sheets><sheet name="Notes" sheetId="1" r:id="rId1"/></sheets></workbook>',
    'xl/_rels/workbook.xml.rels':f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="{R}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
    'xl/worksheets/sheet1.xml':f'<worksheet xmlns="{NS}" xmlns:r="{R}"><sheetData>{"".join(rows)}</sheetData><tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>',
    'xl/worksheets/_rels/sheet1.xml.rels':f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="{R}/table" Target="../tables/table1.xml"/></Relationships>',
    'xl/tables/table1.xml':f'<table xmlns="{NS}" id="1" name="Notes" displayName="Notes" ref="A1:B3"><autoFilter ref="A1:B3"/><tableColumns count="2"><tableColumn id="1" name="name"/><tableColumn id="2" name="value"/></tableColumns></table>'}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
def run(src,out):
    return subprocess.run([sys.executable,str(scripts/'xlsx_insert_rows.py'),str(src),'--sheet','Notes','--insert',json.dumps({'before':3,'values':{'A':'gamma','B':'3'}}),'--out',str(out)],capture_output=True,text=True)
def main():
    with tempfile.TemporaryDirectory(prefix='atlas-workbook-') as t:
        root=Path(t);source=root/'input.xlsx';fixture(source);before=source.read_bytes()
        discovery=subprocess.run([sys.executable,str(scripts/'xlsx_dump.py'),str(source)],capture_output=True,text=True,check=True)
        assert 'Notes' in discovery.stdout and 'A1:B3' in discovery.stdout,discovery.stdout
        target=root/'output.xlsx';result=run(source,target);assert result.returncode==0,result.stdout+result.stderr
        assert source.read_bytes()==before
        with zipfile.ZipFile(target) as z:
            for name in z.namelist():
                if name.endswith('.xml') or name.endswith('.rels'):ET.fromstring(z.read(name))
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            values=[el.text for el in sheet.iter() if el.tag==f'{{{NS}}}t']
            assert values==['name','value','alpha','1','gamma','3','beta','2'],values
            table=ET.fromstring(z.read('xl/tables/table1.xml'))
            assert table.get('ref')=='A1:B4'
            assert table.find(f'{{{NS}}}autoFilter').get('ref')=='A1:B4'
        formula=root/'formula.xlsx';fixture(formula,True)
        assert run(formula,root/'formula-out.xlsx').returncode!=0
        alias=root/'alias.xlsx';alias.symlink_to(source)
        assert run(source,alias).returncode!=0 and source.read_bytes()==before
        print('Discovery, table insertion, inline XML, source preservation, attributed formula and alias refusal passed.')
if __name__=='__main__':main()

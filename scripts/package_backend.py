import argparse, hashlib, json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
ROOT=Path(__file__).resolve().parents[1]
FILES=tuple(sorted(p for p in (ROOT/'backend').rglob('*.py') if '__pycache__' not in p.parts))
def build(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as archive:
        for path in FILES:
            info=ZipInfo(path.relative_to(ROOT).as_posix(),(1980,1,1,0,0,0)); info.compress_type=ZIP_DEFLATED; info.external_attr=0o644 << 16
            archive.writestr(info,path.read_bytes())
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    manifest={"schema":"attendance-spaces-backend-package/v1","sha256":digest,"bytes":output.stat().st_size,"files":[p.relative_to(ROOT).as_posix() for p in FILES]}
    output.with_suffix(output.suffix+'.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,sort_keys=True)); return 0
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=ROOT/'dist/backend.zip'); args=parser.parse_args(); raise SystemExit(build(args.output))

import io
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def _xml_cell(value):
    return f'<c t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>'

def build_attendance_workbook(space, rows):
    headers = ("Checkpoint", "Kind", "Lifecycle", "User", "Fact", "Occurred at", "Participant comment", "Manager note")
    table = [headers] + [tuple(row.get(key, "") for key in ("checkpointId","checkpointKind","lifecycle","userId","factKind","occurredAt","participantComment","managerNote")) for row in rows]
    sheet_rows = ''.join(f'<row r="{index}">{"".join(_xml_cell(value) for value in row)}</row>' for index, row in enumerate(table, 1))
    files = {
      '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
      '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
      'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Attendance" sheetId="1" r:id="rId1"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
      'xl/worksheets/sheet1.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{sheet_rows}</sheetData></worksheet>',
    }
    output=io.BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(files):
            info=ZipInfo(name,(1980,1,1,0,0,0)); info.compress_type=ZIP_DEFLATED; info.external_attr=0o644 << 16
            archive.writestr(info,files[name].encode('utf-8'))
    return output.getvalue()

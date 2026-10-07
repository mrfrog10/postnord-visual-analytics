"""python open_on_sheet.py <src.twbx> <dst.twbx> <sheet or dashboard name>: copy that opens on the given window."""
import re, sys, zipfile
src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
z = zipfile.ZipFile(src)
twb = next(n for n in z.namelist() if n.endswith(".twb"))
x = z.read(twb).decode("utf-8")
x = re.sub(r"(<window class=[\"'](?:worksheet|dashboard)[\"']) maximized=[\"']true[\"']", r"\1", x)
m = re.search(r"<window class=[\"'](dashboard|worksheet)[\"'] name=[\"']%s[\"']>" % re.escape(name), x)
x = x.replace(m.group(0), m.group(0).replace("<window ", '<window maximized="true" ', 1), 1)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as o:
    for i in z.infolist():
        o.writestr(i.filename, x if i.filename == twb else z.read(i.filename))
print("ok", dst)

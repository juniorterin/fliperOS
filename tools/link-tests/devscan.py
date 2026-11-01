import sys, re, collections, xml.etree.ElementTree as ET
pat = re.compile(r"comm|lanc|net|link|serial|modem|ether|lan\b|wan\b|rs232|rs485|uart|sio|usart|dlc|bitb", re.I)
cnt = collections.Counter(); ex = {}
devs = {}
for ev, el in ET.iterparse(sys.stdin.buffer, events=("end",)):
    if el.tag != "machine": continue
    if el.get("isdevice") == "yes":
        devs[el.get("name")] = el.findtext("description") or ""
    else:
        for d in el.findall("device_ref"):
            n = d.get("name")
            if pat.search(n):
                cnt[n] += 1; ex.setdefault(n, []).append(el.get("name"))
    el.clear()
for n, c in cnt.most_common():
    print(c, n, "|", devs.get(n, ""), "|", ",".join(ex[n][:4]))

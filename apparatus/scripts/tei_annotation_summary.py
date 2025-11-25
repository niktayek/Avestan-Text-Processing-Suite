import argparse
from pathlib import Path
from lxml import etree

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tei', required=True)
    args = p.parse_args()
    tei_dir = Path(args.tei)
    rows = []
    for pth in sorted(tei_dir.glob('*.v3.xml')):
        tree = etree.parse(str(pth))
        root = tree.getroot()
        cnt = {'meaningful':0,'trivial':0,'unknown':0}
        for rdg in root.xpath('.//tei:rdg[@resp="score-v3"]', namespaces=NS):
            ana = rdg.get('ana','')
            if '#meaningful' in ana:
                cnt['meaningful'] += 1
            elif '#trivial' in ana:
                cnt['trivial'] += 1
            elif '#unknown' in ana:
                cnt['unknown'] += 1
        rows.append((pth.name, cnt['meaningful'], cnt['trivial'], cnt['unknown']))
    print('file,meaningful,trivial,unknown')
    for r in rows:
        print(','.join(map(str,r)))

if __name__ == '__main__':
    main()

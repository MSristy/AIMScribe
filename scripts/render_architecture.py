"""Render the same Q3 architecture as SVG, PNG and Mermaid; no model/API call."""
from html import escape
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1760, 1580
COLORS = {'implemented': ('#eef9f8', '#167c80'), 'improvement': ('#fff7e6', '#bd7a10'),
          'future': ('#f7f2ff', '#7955a0')}
# Explicit labels distinguish actual implementation from intended connections.
NODES = [
 ('S', 60, 165, 275, 120, 'implemented', ['I | Supplied protocols', '4 protocols; 45 assigned pages', 'Cover = page 1', 'Source ID / edition / page']),
 ('E', 380, 165, 290, 120, 'implemented', ['I | Extract + visual review', 'pypdf text; PDFium images', 'Tables, footnotes, HTN p64', 'Extraction is not clinical inference']),
 ('C', 715, 165, 320, 120, 'implemented', ['I | Curate + validate 32 cards', 'Canonical JSONL; source passages', 'Prerequisites / exclusions / doses', 'card_id + evidence_id + source_id']),
 ('D', 1080, 165, 345, 120, 'implemented', ['I | RAG storage + indexing', 'cards.jsonl -> BM25 JSON index', 'Corpus SHA256; rebuild script', 'No case answers in the index']),
 ('P', 60, 505, 440, 105, 'implemented', ['I | Editable Streamlit input', 'Symptoms, duration, age, history,', 'medicines, allergies; optional details', 'No disease name required']),
 ('V', 60, 655, 440, 105, 'implemented', ['I | Preserve patient context', 'Validation; known facts / unknowns', 'Null != false != assessed none', 'Limited derived facts + provenance']),
 ('R', 590, 505, 460, 105, 'implemented', ['I | Retrieve patient-specific cards', 'BM25 + protocol/category coverage', 'Maximum 10; same hits in both modes', 'Full original evidence stays available']),
 ('X', 590, 705, 460, 110, 'improvement', ['I | TESTED: Improved mode only', 'applicability_preview before model', 'Existing per-card check status', 'Baseline omits only this preview']),
 ('M', 1110, 705, 560, 125, 'implemented', ['I | One configured model request', 'Groq Qwen 3.8 27B selects card / F / Q IDs', 'Clinical fields + sources; F facts / Q slots', 'Full passages are kept in UI / saved records']),
 ('K', 1110, 880, 560, 115, 'implemented', ['I | Shared checks in BOTH modes', 'Schema / retrieved IDs / fact + question refs', 'Limited observed prerequisites + exclusions', 'Unknowns -> clarification / review, not clearance']),
 ('A', 590, 880, 460, 115, 'implemented', ['I | Saved run / experiment evidence', 'Patient, original cards, prompt + response', 'Mode, timing; freeze hash for final batch', 'Expected checklists: evaluation only']),
 ('N', 1110, 1025, 560, 80, 'implemented', ['I | Canonical output renderer', 'Copy source actions / medication fields', 'Exact input facts explain selections']),
 ('U', 1110, 1145, 560, 145, 'implemented', ['I | Recommendation interface', 'Probable diagnoses / investigations', 'Medication planning / advice', 'Source title / version / PDF citations', 'Patient context + missing-info questions']),
 ('NER', 60, 845, 440, 100, 'future', ['F | NER from clinical text', 'Entities + spans, negation, temporality,', 'units and confidence; preserve raw text']),
 ('NR', 60, 985, 440, 80, 'future', ['F | Doctor confirms NER suggestions', 'Resolve ambiguity before patient merge', 'Uncertain values remain unknown']),
 ('DR', 60, 1210, 440, 90, 'future', ['F | Doctor review + acceptance', 'Accept / edit / reject each recommendation', 'Link to run, card + source version']),
 ('RX', 60, 1345, 440, 100, 'future', ['F | Prescription draft assembly', 'Accepted medicine items; verify all fields', 'Doctor resolves gaps + signs before use']),
 ('FB', 585, 1210, 430, 90, 'future', ['F | Doctor feedback store', 'run_id / card_id / source / version', 'Decision, changes, reason + timestamp']),
 ('G', 585, 1345, 430, 100, 'future', ['F | Governed maintenance', 'Review feedback; revalidate source/cards', 'New corpus version + prospective tests', 'No automatic truth labels or training']),
]

# Each edge is also exported to Mermaid. Solid = implemented, dashed = future.
EDGES = [
 ('S','E',[(335,225),(380,225)],False,None),
 ('E','C',[(670,225),(715,225)],False,None),
 ('C','D',[(1035,225),(1080,225)],False,None),
 ('P','V',[(280,610),(280,655)],False,None),
 ('D','R',[(1252,285),(1252,430),(900,430),(900,505)],False,('indexed cards',1060,404)),
 ('V','R',[(500,707),(545,707),(545,558),(590,558)],False,('query',510,625)),
 ('V','M',[(500,682),(535,682),(535,655),(1390,655),(1390,705)],False,('same patient facts in BOTH modes',850,623)),
 ('R','M',[(1050,550),(1510,550),(1510,705)],False,('Baseline: patient + cards',1260,520)),
 ('R','X',[(820,610),(820,705)],False,('Improved path',830,671)),
 ('X','M',[(1050,760),(1110,760)],False,None),
 ('M','K',[(1390,830),(1390,880)],False,None),
 ('K','A',[(1110,938),(1050,938)],False,None),
 ('K','N',[(1390,995),(1390,1025)],False,None),
 ('N','U',[(1390,1105),(1390,1145)],False,None),
 ('NER','NR',[(280,945),(280,985)],True,None),
 ('NR','V',[(60,1025),(30,1025),(30,707),(60,707)],True,None),
 ('U','DR',[(1110,1217),(1070,1217),(1070,1135),(280,1135),(280,1210)],True,('clinician workflow (future)',595,1107)),
 ('DR','RX',[(280,1300),(280,1345)],True,('accepted items',292,1313)),
 ('DR','FB',[(500,1255),(585,1255)],True,None),
 ('FB','G',[(800,1300),(800,1345)],True,None),
 ('G','C',[(1015,1395),(1725,1395),(1725,153),(875,153),(875,165)],True,('reviewed source/card update - not automatic',1210,125)),
]


def main():
    folder = ROOT/'docs'
    folder.mkdir(exist_ok=True)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">Clinical NLP complete architecture: implemented and future components</title>',
           '<desc id="desc">Protocol preparation and canonical-card BM25 retrieval feed one model call and common checks; Improved adds a pre-model applicability preview. Future NER is confirmed before input; future doctor acceptance, prescription drafts and governed feedback connect after output.</desc>',
           '<rect width="100%" height="100%" fill="#ffffff"/>']
    canvas = Image.new('RGB', (WIDTH, HEIGHT), 'white')
    draw = ImageDraw.Draw(canvas)
    font_dir = Path('C:/Windows/Fonts')
    def font(size, bold=False):
        return ImageFont.truetype(str(font_dir/('segoeuib.ttf' if bold else 'segoeui.ttf')), size)
    def text(x, y, value, size=21, color='#17324d', bold=False):
        svg.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{escape(value)}</text>')
        draw.text((x,y), value, font=font(size,bold), fill=color)
    def rect(x,y,w,h,fill,stroke,dashed=False,radius=13):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"'+(' stroke-dasharray="8 6"' if dashed else '')+'/>')
        draw.rounded_rectangle((x,y,x+w,y+h), radius=radius, fill=fill, outline=stroke, width=2)
        # Dashed arrows and explicit F labels distinguish futures in the PNG.
    text(45,24,'Clinical NLP | Complete recommender architecture',34,bold=True)
    text(45,70,'I = implemented prototype     F = future design only     Orange = tested optional preview     Dashed arrows = future connections',21)
    groups = [(35,110,1690,295,'OFFLINE | Protocol preparation and source provenance'),
              (35,455,490,330,'INPUT | Patient facts remain available throughout'),
              (560,455,1140,675,'RUNTIME | Shared pipeline'),
              (35,795,490,300,'FUTURE | NER input connector'),
              (35,1160,1010,315,'FUTURE | Clinician workflow and governed feedback')]
    for x,y,w,h,title in groups:
        rect(x,y,w,h,'#fafcfe','#d6e0ea')
        text(x+16,y+12,title,19,bold=True)
    text(60,307,'Provenance travels with evidence: source ID + title/version + PDF page -> evidence ID -> card ID -> output references',21)
    for source,target,points,future,label in EDGES:
        color = '#7955a0' if future else '#376277'
        coords = ' '.join(f'{x},{y}' for x,y in points)
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"'+(' stroke-dasharray="9 7"' if future else '')+'/>')
        if future:
            for (x1,y1),(x2,y2) in zip(points,points[1:]):
                length = abs(x2-x1)+abs(y2-y1)
                for start in range(0,length,16):
                    stop=min(start+9,length)
                    draw.line((x1+(x2-x1)*start/length,y1+(y2-y1)*start/length,
                               x1+(x2-x1)*stop/length,y1+(y2-y1)*stop/length),fill=color,width=3)
        else:
            draw.line(points,fill=color,width=3)
        (px,py),(ex,ey) = points[-2:]
        dx,dy = ex-px,ey-py
        if abs(dx)>abs(dy):
            arrow=[(ex,ey),(ex-(11 if dx>0 else -11),ey-6),(ex-(11 if dx>0 else -11),ey+6)]
        else:
            arrow=[(ex,ey),(ex-6,ey-(11 if dy>0 else -11)),(ex+6,ey-(11 if dy>0 else -11))]
        svg.append(f'<polygon points="'+ ' '.join(f'{x},{y}' for x,y in arrow)+f'" fill="{color}"/>')
        draw.polygon(arrow, fill=color)
        if label:
            value,x,y = label
            text(x,y,value,18,color)
    for _,x,y,w,h,kind,lines in NODES:
        h = max(h, len(lines)*25+20)
        fill,stroke = COLORS[kind]
        rect(x,y,w,h,fill,stroke,dashed=kind=='future')
        for i,line in enumerate(lines):
            size = 20 if i else 22
            while font(size,i==0).getlength(line) > w-28:
                size -= 1
            text(x+14,y+11+i*25,line,size,bold=i==0)
    text(45,1501,'Full source passages stay in canonical cards / retrieved records / UI; the model receives the readable clinical-field projection.',21)
    text(45,1534,'Limited checks are not full clinical validation. Frozen expected answers remain outside prompts and the retrieval index.',21)
    svg.append('</svg>')
    (folder/'architecture.svg').write_text('\n'.join(svg),encoding='utf-8')
    canvas.save(folder/'architecture.png')
    mermaid=['flowchart TB']
    for key,_,_,_,_,kind,lines in NODES:
        mermaid.append(f'  {key}["'+ '<br/>'.join(escape(line) for line in lines)+'"]')
    for source,target,_,future,label in EDGES:
        mermaid.append(f'  {source} '+('-.->' if future else '-->')+' '+target)
    for kind,(fill,stroke) in COLORS.items():
        mermaid.append(f'  classDef {kind} fill:{fill},stroke:{stroke},color:#17324d;')
        mermaid.append('  class '+','.join(n[0] for n in NODES if n[5]==kind)+' '+kind+';')
    (folder/'architecture.mmd').write_text('\n'.join(mermaid)+'\n',encoding='utf-8')
    print(json.dumps({'diagram':'docs/architecture.svg','preview':'docs/architecture.png',
                      'editable_mermaid':'docs/architecture.mmd','nodes':len(NODES),'edges':len(EDGES)}))


if __name__ == '__main__':
    main()

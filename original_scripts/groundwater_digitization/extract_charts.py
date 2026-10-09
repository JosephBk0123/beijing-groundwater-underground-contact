from pathlib import Path
import fitz, json
from PIL import Image
D=Path('/mnt/data'); O=D/'district_digitization_v1'; W=O/'work'
pages={2001:7,2002:15,2003:17,2004:16,2006:15,2007:13,2008:12,2009:12,2010:12,2012:14,2013:13,2014:13,2015:13,2016:12,2017:13,2018:13,2019:13,2020:13,2021:13,2022:13,2023:13,2024:13,2025:13}
meta={}
for y,n in pages.items():
 doc=fitz.open(D/f'gb{y}.pdf'); page=doc[n-1]; ims=page.get_images(full=True)
 if y in [2012,2016,2020]:
  page.get_pixmap(matrix=fitz.Matrix(3,3)).save(W/f'{y}_page.png')
  # Charts on upper / lower parts for these pages
  crop={2012:fitz.Rect(30,365,570,705),2016:fitz.Rect(55,50,530,346),2020:fitz.Rect(45,45,545,357)}[y]
  pix=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=crop)
  pix.save(W/f'{y}_native.png')
  meta[y]={'pdf_page':n,'type':'page_render','clip':list(crop),'render_scale':3}
 else:
  # choose the chart image, not full-page background or the monthly/long-term chart
  idx={2001:1,2002:2,2003:0,2004:0,2006:0,2007:0,2008:1,2009:1,2010:1,2013:1,2014:1,2015:0,2017:0,2018:0,2019:0,2021:0,2022:0,2023:0,2024:0,2025:1}[y]
  xref=ims[idx][0]; data=doc.extract_image(xref)
  (W/f'{y}_image.{data["ext"]}').write_bytes(data['image'])
  im=Image.open(W/f'{y}_image.{data["ext"]}').convert('RGB'); im.save(W/f'{y}_native.png')
  meta[y]={'pdf_page':n,'type':'embedded_raster','xref':xref,'size':list(im.size)}
(O/'source_extract_manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
print('Extracted',len(meta),'charts')

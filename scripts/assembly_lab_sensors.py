"""Read complete HWiNFO rows without altering the running logger."""
import csv,datetime,io,math
from pathlib import Path

def parse_sample(headers,row,offset_minutes):
 if len(row)!=len(headers):raise ValueError('Partial sensor row')
 local=datetime.datetime.strptime(row[0]+' '+row[1],'%d.%m.%Y %H:%M:%S.%f')
 zone=datetime.timezone(datetime.timedelta(minutes=offset_minutes));counts={};values={}
 for key,value in zip(headers[2:],row[2:]):
  counts[key]=counts.get(key,0)+1
  values[key if counts[key]==1 else key+' #'+str(counts[key])]=value
 return {'utc':local.replace(tzinfo=zone).astimezone(datetime.timezone.utc).isoformat(),'values':values}

class Sensors:
 def __init__(self,path,offset_minutes):
  self.path=Path(path);self.offset=offset_minutes
  with self.path.open('rb') as f:header=f.readline()
  try:header.decode('utf-8-sig');self.encoding='utf-8-sig'
  except UnicodeDecodeError:self.encoding='cp1252'
  self.headers=next(csv.reader([header.decode(self.encoding)]))
  required=['CPU (Tctl/Tdie) [°C]','CPU PPT [W]','CPU PPT Limit [%]','Thermal Throttling (HTC) [Yes/No]','Thermal Throttling (PROCHOT CPU) [Yes/No]','Thermal Throttling (PROCHOT EXT) [Yes/No]']
  if any(k not in self.headers for k in required):raise ValueError('Required CPU sensors missing')
 def latest(self):
  with self.path.open('rb') as f:
   f.seek(0,2);size=f.tell();f.seek(max(0,size-128*1024));raw=f.read()
  lines=raw.split(b'\n')[:-1]
  for line in reversed(lines):
   try:return parse_sample(self.headers,next(csv.reader([line.decode(self.encoding)])),self.offset)
   except (ValueError,UnicodeDecodeError,csv.Error):continue
  raise ValueError('No complete sensor row')
 def safety(self,sample,now=None):
  now=now or datetime.datetime.now(datetime.timezone.utc)
  age=(now-datetime.datetime.fromisoformat(sample['utc'])).total_seconds()
  if not -5<=age<=15:return 'HWiNFO data is stale or clock offset is incorrect'
  values=sample['values']
  for key in ('Thermal Throttling (HTC) [Yes/No]','Thermal Throttling (PROCHOT CPU) [Yes/No]','Thermal Throttling (PROCHOT EXT) [Yes/No]'):
   if values[key]!='No':return 'CPU thermal-throttling flag: '+key
  try:temp=float(values['CPU (Tctl/Tdie) [°C]']);ppt=float(values['CPU PPT [W]']);limit=float(values['CPU PPT Limit [%]'])
  except ValueError:return 'Invalid CPU safety sensor'
  if not all(math.isfinite(v) for v in (temp,ppt,limit)):return 'Invalid CPU safety sensor'
  if temp>=85:return 'Conservative test stop at 85 C; not a CPU temperature specification'
  if ppt>145 or limit>0 and ppt/(limit/100)>145:return 'Observed/inferred PPT exceeds the existing approximately 142 W envelope'
  return None

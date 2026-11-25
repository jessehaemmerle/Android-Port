import re,sys
def blocks(path):
    """label -> normalized text of node body (brace matched)"""
    s=open(path).read()
    s=re.sub(r'/\*.*?\*/','',s,flags=re.S); s=re.sub(r'//[^\n]*','',s)
    out={}
    for m in re.finditer(r'([A-Za-z0-9_]+):\s*[A-Za-z0-9_@,.\-]+\s*\{',s):
        i=m.end(); d=1
        while d and i<len(s):
            d+= (s[i]=='{')-(s[i]=='}'); i+=1
        out.setdefault(m.group(1),re.sub(r'\s+',' ',s[m.start():i]).strip())
    return out
op=blocks('kop1/arch/arm/boot/dts/qcom/msm8996-pinctrl.dtsi')
nw={}
import glob
for f in glob.glob('k44/arch/arm64/boot/dts/qcom/msm8996*.dtsi')+glob.glob('k44/arch/arm64/boot/dts/qcom/msm-*.dtsi'):
    for k,v in blocks(f).items(): nw.setdefault(k,v)
miss=[k for k in op if k not in nw]
diff=[k for k in op if k in nw and re.sub(r'^[^{]*','',op[k])!=re.sub(r'^[^{]*','',nw[k])]
print(len(op),'op labels;',len(miss),'missing;',len(diff),'differ');print('missing',miss);print('differ',diff[:60])

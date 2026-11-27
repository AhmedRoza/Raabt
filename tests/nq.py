import asyncio,json
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=await b.new_page(viewport={'width':1180,'height':800}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(4000)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(500)
    L=lambda i,t,extra='':"{kind:'link',id:'%s',title:'%s',url:'https://%s.example',tags:[]%s}"%(i,t,i,extra)
    await pg.evaluate("S.vault=[%s,%s,%s,%s,{kind:'folder',id:'F',title:'مجلد',color:'#2ecc71',shape:0,pinned:true,children:[]}];S.settings.view='list';prep(S.vault);render()"%(L('a','A',',opens:5,last:Date.now()'),L('b','B',',opens:2,last:Date.now()-5000'),L('c','C'),L('d','D')))
    ids=lambda:pg.evaluate("[...document.querySelectorAll('#main .card[data-id]')].map(c=>c.dataset.id).join(',')")
    print('order',await ids())
    # pin: size, no glow, left edge
    r=await pg.evaluate("(()=>{const p=document.querySelector('.card[data-id=F] .pin'),c=document.querySelector('.card[data-id=F]');if(!p)return null;const a=p.getBoundingClientRect(),k=c.getBoundingClientRect();return [Math.round(a.width),getComputedStyle(p).filter,Math.round(a.left-k.left),Math.round(k.right-a.right)]})()")
    print('pin',r); ok('pin 26px, no filter glow, near physical left edge',r and r[0]>=24 and r[1]=='none' and r[2]<r[3] and r[2]<40)
    # double click enters folder, single click does not
    await pg.click('.card[data-id=F] .nm',click_count=1); await pg.wait_for_timeout(300)
    ok('single click does not enter',await pg.evaluate("UI.path.length")==0)
    await pg.dblclick('.card[data-id=F] .nm'); await pg.wait_for_timeout(300)
    ok('double click enters',await pg.evaluate("UI.path.length")==1); await pg.evaluate("UI.path=[];render()")
    # between-link reorder: drag d between a and b, persisted
    box=await pg.evaluate("(()=>{const r=document.querySelector('.card[data-id=a]').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
    bb=await pg.evaluate("(()=>{const r=document.querySelector('.card[data-id=b]').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
    # drop at top edge of b (between a and b)
    await pg.drag_and_drop('.card[data-id=d]','.card[data-id=b]',target_position={'x':bb[2]/2,'y':3}); await pg.wait_for_timeout(500)
    o=await pg.evaluate("S.vault.map(n=>n.id).join(',')"); print('after',o,await pg.evaluate("document.querySelectorAll('.card.xt, .dlg').length"))
    ok('link moved between links, no merge',o.replace('F,','').split(',').index('d')==o.replace('F,','').split(',').index('b')-1 and 'd' in o.split(',') and not any(n.get('kind')=='folder' and n['id']!='F' for n in json.loads(await pg.evaluate("JSON.stringify(S.vault)"))),o)
    await pg.wait_for_timeout(500)
    o2=await pg.evaluate("(async()=>JSON.parse(await B.load('vault.json')).vault.map(n=>n.id).join(','))()"); ok('order saved to vault.json (storage bridge)',o2==o,o2)
    # separators
    sp=await pg.evaluate("(()=>{const x=document.querySelector('.dr');return x?getComputedStyle(x).borderBottomWidth+' '+getComputedStyle(x).borderBottomColor:null})()")
    print('sep',sp)
    # dashboard link colours scoped
    await pg.evaluate("S.vault=[%s,%s,%s];S.settings.view='grid';prep(S.vault);render()"%(L('a','A',',opens:5,last:Date.now()'),L('b','B',',opens:2,last:Date.now()-5000'),L('c','C')))
    await pg.wait_for_timeout(300)
    col=await pg.evaluate("""(()=>{const g=e=>e?getComputedStyle(e).color:null;return {dash:[...document.querySelectorAll('.dash .dr')].map(x=>g(x.querySelector('.nm,b,.t,a,div:nth-child(2)>*:first-child'))),card:g(document.querySelector('#main .card.lnk .nm')),tx:getComputedStyle(document.body).color,ac:getComputedStyle(document.documentElement).getPropertyValue('--ac2')}})()""")
    print(col); ok('dash link colour differs from card name colour',col['dash'] and col['dash'][0]!=col['card'])
    await pg.screenshot(path='/downloads/shot_dash_colors.png')
    # trash collapsed, instagram footer
    await pg.evaluate("S.trash=[{n:{kind:'link',id:'t1',title:'T',url:'https://t.example'},at:1,path:[]}];UI.tab='settings';UI.trashOpen=false;render()"); await pg.wait_for_timeout(300)
    ok('trash closed by default',await pg.evaluate("!document.getElementById('trashd').open"))
    ok('instagram footer link present',await pg.evaluate("!!document.querySelector('.igrow')&&document.querySelector('.igrow').innerText.trim()==='Instagram'"))
    await pg.evaluate("document.getElementById('trashd').querySelector('summary').click()"); await pg.wait_for_timeout(200)
    ok('trash opens on click',await pg.evaluate("document.getElementById('trashd').open"))
    # refetch with mocked meta
    await pg.evaluate("UI.tab='vault';UI.path=[];render();B.meta=async u=>({image:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAHnOcQAAAAABJRU5ErkJggg=='});S.vault.push({kind:'folder',id:'G',title:'g',color:'#fff',shape:0,children:[%s]});prep(S.vault);render()"%L('z','Z'))
    await pg.evaluate("void refetchHere()"); await pg.wait_for_timeout(800)
    r=await pg.evaluate("[S.vault.filter(n=>n.kind=='link').map(n=>!!n.img).join(),find('z').n.img?1:0]"); print(r)
    ok('refetch only current folder direct links',r[0]=='true,true,true' and r[1]==0,r)
    print('errors',errs,sum(R),'/',len(R)); await b.close()
asyncio.run(main())

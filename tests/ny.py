import asyncio,json,base64,os,glob
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    ctx=await b.new_context(accept_downloads=True,viewport={'width':1180,'height':760}); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(4000)
    store={}
    def w(sub,name,b64,first,last):
        store.setdefault((sub,name),[]).append(b64); return True
    await pg.expose_function('rbBinWrite',w)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
    await pg.evaluate("""S.vault=[{kind:'folder',id:'f1',title:'دراسة',color:'#ff4d6d',shape:2,children:[{kind:'folder',id:'f2',title:'داخل',color:'#22d3ee',shape:1,children:[{kind:'link',id:'l3',title:'Deep',url:'https://deep.example/x',tags:['x']}]}]},{kind:'folder',id:'f3',title:'تاني',color:'#2ecc71',shape:0,children:[]},{kind:'link',id:'l1',title:'Example',url:'https://example.com',tags:['a'],opens:2,pinned:true},{kind:'link',id:'l2',title:'Other',url:'https://o.example',tags:[]}];prep(S.vault);S.settings.sideOpen=false;render()""")
    # themes contrast
    r=await pg.evaluate("""()=>THEMES.map((t,i)=>{S.settings.theme=i;applyTheme();const cs=getComputedStyle(document.documentElement);return [t[0],cs.getPropertyValue('--bg').trim(),cs.getPropertyValue('--accent').trim()||cs.getPropertyValue('--ac').trim(),cs.getPropertyValue('--on').trim()]})""")
    print(r[:4]); ok('15 themes',len(r)==15); ok('all black bg',all(x[1] in('#000','#000000') for x in r),[x[1] for x in r if x[1] not in('#000','#000000')])
    await pg.evaluate("S.settings.theme=0;applyTheme()")
    # navigation: double-click folder enters
    await pg.dblclick('.card.fol >> nth=0'); ok('dblclick enters folder',await pg.evaluate("UI.path.length")==1)
    await pg.click('[data-act=back]'); ok('back',await pg.evaluate("UI.path.length")==0)
    await pg.click('[data-act=fwd]'); ok('fwd',await pg.evaluate("UI.path.length")==1)
    await pg.click('[data-act=up]'); ok('up',await pg.evaluate("UI.path.length")==0)
    await pg.dblclick('.card.fol >> nth=0'); await pg.keyboard.press('Alt+ArrowLeft'); ok('alt+left',await pg.evaluate("UI.path.length")==0)
    # side panel
    await pg.click('[data-act=side]'); await pg.wait_for_timeout(300); ok('side open',await pg.evaluate("!$('#side').hidden"))
    await pg.screenshot(path='/tmp/shot_side.png')
    # tab drag hover
    ok('images tab',await pg.evaluate("document.querySelector('[data-tab=images]')!==null"))
    await pg.click('[data-tab=images]'); await pg.wait_for_timeout(200)
    png=open('/tmp/t.png','rb').read()
    await pg.evaluate("""async(b)=>{const u=Uint8Array.from(atob(b),c=>c.charCodeAt(0));await addImages([new File([u],'a.png',{type:'image/png'})])}""",base64.b64encode(png).decode())
    await pg.wait_for_timeout(500); ok('image added',await pg.evaluate("S.images.length")==1,await pg.evaluate("JSON.stringify(S.images[0]||{})"))
    ok('image bridge written',len(store)==2)
    await pg.screenshot(path='/tmp/shot_img.png')
    # backup scopes json
    for sc in('vault','imports','both'):
        j=json.loads(await pg.evaluate("(s)=>backupJson(s)",sc)); ok('backup '+sc,j['scope']==sc and ('images' in j['state'])==(sc!='imports'))
    # narrow header
    await pg.evaluate('setSide(false)'); await pg.set_viewport_size({'width':400,'height':760}); await pg.click('[data-tab=vault]'); await pg.wait_for_timeout(300); await pg.screenshot(path='/tmp/shot_narrow.png')
    await pg.click('[data-tab=imports]'); await pg.wait_for_timeout(300); await pg.screenshot(path='/tmp/shot_narrow2.png')
    print('errors',errs,sum(R),'/',len(R))
asyncio.run(main())

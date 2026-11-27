import asyncio,base64,time
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=await b.new_page(viewport={'width':1180,'height':760}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(5000)
    files={}
    def w(sub,name,b64,first,last):
        k=(sub,name); files[k]=(b'' if first else files.get(k,b''))+base64.b64decode(b64); return True
    async def sz(sub,name): return len(files[(sub,name)]) if (sub,name) in files else -1
    async def rd(sub,name,off,n): 
        d=files.get((sub,name)); return base64.b64encode(d[off:off+n]).decode() if d is not None else ''
    async def dl(sub,name): files.pop((sub,name),None); return True
    for n,f in (('rbBinWrite',w),('rbBinSize',sz),('rbBinRead',rd),('rbBinDel',dl)): await pg.expose_function(n,f)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(500)
    png=open('/tmp/t.png','rb').read()
    await pg.click('[data-tab=images]')
    await pg.evaluate("""async(b)=>{const u=Uint8Array.from(atob(b),c=>c.charCodeAt(0));await addImages([new File([u],'a.png',{type:'image/png'})])}""",base64.b64encode(png).decode())
    await pg.wait_for_timeout(800)
    ok('original bytes stored exactly',files.get(('images',[k for s,k in files if not k.endswith('.t.webp')][0]))==png)
    await pg.screenshot(path='/tmp/shot_img2.png')
    th=await pg.evaluate("(()=>{const e=document.querySelector('#main [data-th]');return e?[e.tagName,getComputedStyle(e).backgroundImage.slice(0,30),e.naturalWidth||0]:null})()")
    ok('thumbnail painted',th and 'url' in th[1],th)
    await pg.evaluate("void viewImage(S.images[0].id)"); await pg.wait_for_timeout(700); await pg.screenshot(path='/tmp/shot_imgfull.png'); await pg.click('[data-x]')
    ok('full image viewer shows',await pg.evaluate("(()=>{const i=document.querySelector('#imgv');return i?i.naturalWidth:0})()")==300)
    # tab drag gesture
    await pg.evaluate("S.vault=[{kind:'link',id:'a',title:'A',url:'https://a.example'}];S.imports=[];prep(S.vault);UI.tab='vault';render()")
    bx=await pg.locator('.card[data-id=a]').bounding_box(); tb=await pg.locator('[data-tab=imports]').bounding_box()
    await pg.mouse.move(bx['x']+bx['width']/2,bx['y']+bx['height']/2); await pg.mouse.down(); await pg.mouse.move(bx['x']+bx['width']/2+30,bx['y']+20,steps=3)
    await pg.mouse.move(tb['x']+tb['width']/2,tb['y']+tb['height']/2,steps=12); await pg.wait_for_timeout(900)
    ok('hover switches tab',await pg.evaluate("UI.tab")=='imports')
    await pg.mouse.up(); await pg.wait_for_timeout(500)
    ok('drop on tab moves link',await pg.evaluate("[S.vault.length,S.imports.map(x=>x.id).join()]")==[0,'a'],await pg.evaluate("JSON.stringify([S.vault.length,S.imports.length,UI.tab])"))
    # tags clear with timing
    await pg.evaluate("S.vault=[{kind:'link',id:'a',title:'A',url:'https://a.example',tags:['x','y']}];prep(S.vault);UI.tab='settings';render()")
    await pg.click('[data-act=cleartags]'); t0=time.time()
    await pg.wait_for_timeout(300)
    ok('locked at start',await pg.evaluate("document.querySelector('[data-ok=\"1\"]').disabled"))
    await pg.wait_for_timeout(5000); ok('still locked at 5s',await pg.evaluate("document.querySelector('[data-ok=\"1\"]').disabled"))
    await pg.wait_for_timeout(5200); en=await pg.evaluate("!document.querySelector('[data-ok=\"1\"]').disabled"); ok('enabled after ~10s',en,round(time.time()-t0,1))
    await pg.click('[data-x]'); await pg.wait_for_timeout(200); ok('cancel keeps tags',await pg.evaluate("S.vault[0].tags.length")==2)
    await pg.click('[data-act=cleartags]'); await pg.wait_for_timeout(10500); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('confirm clears tags',await pg.evaluate("S.vault[0].tags.length")==0)
    print('errors',errs,sum(R),'/',len(R))
asyncio.run(main())

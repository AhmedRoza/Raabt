import asyncio,base64,glob,os
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=await b.new_page(viewport={'width':1180,'height':760}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(5000)
    await pg.expose_function('rbFont',lambda n: base64.b64encode(open('/home/sandbox/raabt/shell/fonts/'+n,'rb').read()).decode() if os.path.exists('/home/sandbox/raabt/shell/fonts/'+n) else '')
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(500)
    keys=await pg.evaluate("Object.keys(FB)")
    bad=[]
    for k in keys:
        await pg.evaluate("(k)=>{S.settings.fontSel='b:'+k;applyFont()}",k); await pg.wait_for_timeout(250)
        r=await pg.evaluate("(k)=>document.fonts.check('16px \"'+FB[k][0]+'\"','%s')"%("مرحبا" ),k)
        r2=await pg.evaluate("(k)=>[...document.fonts].filter(f=>f.family.replace(/\"/g,'')===FB[k][0]&&f.status==='loaded').length",k)
        if not r2: bad.append(k)
    ok('all 14 bundled fonts load',not bad,bad)
    # user fonts via addFonts
    fs=sorted(glob.glob('/downloads/file-*.bin'))
    res=await pg.evaluate("""async(arr)=>{const fl=arr.map(([n,b])=>new File([Uint8Array.from(atob(b),c=>c.charCodeAt(0))],n));await addFonts(fl);return S.settings.userFonts.length}""",[[os.path.basename(f)+'.ttf',base64.b64encode(open(f,'rb').read()).decode()] for f in fs])
    ok('user fonts accepted (%d files)'%len(fs),res==len(fs),res)
    await pg.evaluate("S.settings.fontSel='u:'+S.settings.userFonts[0].id;applyFont()"); await pg.wait_for_timeout(500)
    ok('user font applied',await pg.evaluate("document.fonts.check('16px UF'+S.settings.userFonts[0].id)"))
    # tags clear confirm lock
    await pg.evaluate("S.vault=[{kind:'link',id:'a',title:'A',url:'https://a.example',tags:['x','y']}];prep(S.vault);UI.tab='settings';render()")
    await pg.click('[data-act=cleartags]'); await pg.wait_for_timeout(400)
    dis=await pg.evaluate("document.querySelector('[data-ok=\"1\"]').disabled"); ok('clear tags confirm disabled at first',dis)
    await pg.evaluate("document.querySelector('[data-x]')&&document.querySelector('[data-x]').click()")
    # dashboard
    await pg.evaluate("S.vault=[{kind:'link',id:'a',title:'A',url:'https://a.example',tags:[],opens:3,lastOpened:Date.now()}];prep(S.vault);S.settings.sideOpen=false;UI.tab='vault';render()")
    ok('dashboard cards exist',await pg.evaluate("document.querySelectorAll('.dash .dcard, .dcard, .dash').length")>0)
    print('errors',errs,sum(R),'/',len(R))
asyncio.run(main())

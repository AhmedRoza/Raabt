import asyncio,json
from playwright.async_api import async_playwright
R=[]
def ok(n,c): R.append(bool(c)); print('PASS' if c else 'FAIL',n)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1180,'height':800}); errs=[]; pg.set_default_timeout(4000)
        pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
        # old v1 backup (exact old shape, no scope, no images)
        v1={'format':'raabt-backup','version':1,'saved_at':1,'state':{'vault':[{'kind':'folder','id':'o1','title':'قديم','color':'#ff0','shape':0,'children':[{'kind':'link','id':'o2','title':'old link','url':'https://old.example'}]}],'imports':[{'kind':'folder','id':'o3','title':'Firefox','children':[{'kind':'link','id':'o4','title':'imp','url':'https://imp.example'}]}],'trash':[],'counters':{'Firefox':1},'settings':{'theme':2,'view':'list','pin':''}}}
        await pg.evaluate("S.vault=[{kind:'link',id:'x',title:'new',url:'https://n.example'}];prep(S.vault);render()")
        void_=pg.evaluate("(t)=>{void restoreBackup(t)}",json.dumps(v1)); await void_
        await pg.wait_for_timeout(300)
        await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(500)
        r=await pg.evaluate("[S.vault[0]&&S.vault[0].title,S.imports[0]&&S.imports[0].title,S.settings.view,Array.isArray(S.images),S.settings.pin]")
        print(r); ok('v1 restore vault+imports',r[0]=='قديم' and r[1]=='Firefox'); ok('v1 settings applied, images array safe',r[2]=='list' and r[3])
        # hotkey capture UI
        await pg.evaluate("S.settings.hotkey=false;showSettings&&showSettings()") if False else None
        found=await pg.evaluate("typeof captureHotkey")
        ok('captureHotkey exists',found=='function')
        btn=await pg.evaluate("(()=>{const b=document.createElement('button');b.id='hkt';document.body.appendChild(b);return 1})()")
        await pg.evaluate("window.rbHotkey=async(on,m,v)=>{window.__hk=[on,m,v];return window.__hkok!==false};captureHotkey(document.getElementById('hkt'))")
        await pg.keyboard.press('Control+Alt+KeyK'); await pg.wait_for_timeout(300)
        r=await pg.evaluate("[S.settings.hkLabel,S.settings.hkMods,S.settings.hkVk]"); print(r); ok('capture Ctrl+Alt+K',r[0]=='Ctrl+Alt+K' and r[1]==3)
        await pg.evaluate("S.settings.hotkey=true;window.__hkok=false;captureHotkey(document.getElementById('hkt'))")
        await pg.keyboard.press('Control+Shift+KeyL'); await pg.wait_for_timeout(300)
        ok('rejected (in use) rolls back',await pg.evaluate("S.settings.hkLabel")=='Ctrl+Alt+K')
        await pg.evaluate("window.__hkok=true;captureHotkey(document.getElementById('hkt'))")
        await pg.keyboard.press('KeyA'); await pg.wait_for_timeout(300)
        ok('no modifier rejected',await pg.evaluate("S.settings.hkLabel")=='Ctrl+Alt+K')
        await pg.evaluate("captureHotkey(document.getElementById('hkt'))"); await pg.keyboard.press('Control+Alt+F5'); await pg.wait_for_timeout(300)
        ok('F5 accepted',await pg.evaluate("S.settings.hkLabel")=='Ctrl+Alt+F5')
        print('errors',errs,sum(R),'/',len(R)); await b.close()
asyncio.run(main())

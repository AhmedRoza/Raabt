import asyncio,zipfile,json,re
from playwright.async_api import async_playwright
R=[]
def ok(n,c): R.append(bool(c)); print('PASS' if c else 'FAIL',n,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    ctx=await b.new_context(accept_downloads=True,viewport={'width':1180,'height':760}); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(4000)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
    await pg.evaluate("""S.vault=[{kind:'folder',id:'f1',title:'دراسة',color:'#ff4d6d',shape:2,children:[{kind:'folder',id:'f2',title:'داخل',color:'#22d3ee',shape:1,children:[{kind:'link',id:'l3',title:'Deep & <b>',url:'https://deep.example/x?a=1&b=2',tags:['x'],hist:[],opens:0,added:1}]}],hist:[],added:1},{kind:'link',id:'l1',title:'Example',url:'https://example.com',tags:['تعلم','شغل'],hist:[],opens:2,added:1,pinned:true}];S.imports=[{kind:'folder',id:'i1',title:'Firefox',browser:'Firefox',color:'#f60',shape:1,children:[{kind:'link',id:'l9',title:'Imp',url:'https://imp.example',tags:[],hist:[],opens:0,added:1}],hist:[],added:1}];prep(S.vault);prep(S.imports);UI.tab='vault';render()""")
    ok('no errors on render',not errs)
    # tags widget
    await pg.click('[data-act=add]'); await pg.click('#pop [data-pk=l]'); await pg.fill('#dlg input[name=url]','t.example'); await pg.fill('#tgin','تعلم'); await pg.keyboard.press('Enter'); await pg.fill('#tgin','جديد'); await pg.keyboard.press(','); await pg.click('[data-ok="1"]')
    ok('tag chips saved',await pg.evaluate("S.vault.at(-1).tags.join('|')")=='تعلم|جديد')
    # export every format x scope
    for fmt in ('html','xlsx','docx','pdf'):
      for sc in ('vault','imports','both','node:f1'):
        await pg.evaluate("UI.sel=new Set()")
        try:
          async with pg.expect_download(timeout=4000) as d:
            await pg.evaluate("(a)=>{const f=a[0],sc=a[1];exportDlg(f,sc.startsWith('node:')?find(sc.slice(5)).n:null)}",[fmt,sc])
            await pg.wait_for_timeout(200)
            if sc.startswith('node:'): pass
            else: await pg.select_option('#xsc',sc)
            await pg.click('[data-ok="1"]')
          dl=await d.value; path=f'/tmp/o_{fmt}_{sc.replace(":","_")}.'+fmt; await dl.save_as(path); ok(f'{fmt} {sc} downloaded',True)
        except Exception as e:
          if fmt=='pdf':
            await pg.wait_for_timeout(600)
            ok(f'pdf {sc} print route',await pg.evaluate("window.__pr!==undefined"))
          else: ok(f'{fmt} {sc} ERR {str(e)[:60]}',False)
          await pg.evaluate("document.getElementById('veil').style.display='none'")
    print('errors',errs); print(sum(R),'/',len(R))
asyncio.run(main())

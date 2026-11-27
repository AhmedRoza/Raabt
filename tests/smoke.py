import asyncio
from playwright.async_api import async_playwright
SEED="""S.vault=[{kind:'folder',id:'F1',title:'مجلد',children:[{kind:'link',id:'L1',title:'رابط',url:'https://a.test',tags:['t'],hist:[],added:Date.now()}],color:'#7c5cff',shape:0,tags:[],hist:[],added:Date.now()},{kind:'link',id:'L2',title:'رابط 2',url:'https://b.test',tags:[],hist:[],added:Date.now(),note:'ملاحظة'}];
S.subjects=[{kind:'folder',subj:true,id:'S1',title:'مادة',status:'done',color:'#00e0ff',shape:0,children:[]}];S.imports=[];prep(S.vault);prep(S.subjects);render()"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=await b.new_page(viewport={'width':1180,'height':820}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('console',lambda m: errs.append('console:'+m.text) if (m.type=='error' and 'playfair-display-latin' not in m.text and 'ERR_FAILED' not in m.text) else None)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(700)
    await pg.evaluate(SEED); await pg.wait_for_timeout(300)
    for tab in ['vault','subjects','imports','images','settings']:
        for view in ['grid','list','tree','album','explorer','mac','hex']:
            await pg.evaluate(f"UI.tab='{tab}';S.settings.view='{view}';render();0"); await pg.wait_for_timeout(60)
    # dialogs
    for fn in ['addLink(\'vault\')','addFolder(\'vault\')','addSubject()','manualBackup()','askScope(\'تست\',\'تم\')','searchAll(S.vault,"رابط")','(()=>{UI.trashOpen=true;render()})()','exportDlg()','editNode(\'F1\')','editNode(\'L1\')','subjectStatus(\'S1\')','quickNote(\'L1\')','addToSubject([\'L2\'])','pickTree(\'تست\',\'تم\')','pickSubjects()','showMenu(\'F1\',\'vault\',50,50)']:
        await pg.evaluate(f"void {fn}"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.querySelectorAll('#dlg [data-x]').forEach(b=>b.click());document.querySelector('#veil').style.display='none';document.querySelector('#pop').style.display='none';0")
    print('errors',errs)
    print('OK' if not errs else 'FAIL')
    await b.close()
asyncio.run(main())

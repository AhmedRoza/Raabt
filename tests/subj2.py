import asyncio
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
SEED="""S.vault=[{kind:'link',id:'L1',title:'Example',url:'https://example.com'}];
S.subjects=[{kind:'folder',subj:true,id:'S1',title:'رياضيات 2',color:'#00e0ff',shape:0,status:'done',children:[{kind:'link',id:'M1',title:'سلايدات',url:'https://math.test'}]},
 {kind:'folder',subj:true,id:'S2',title:'فيزياء',color:'#ffb703',shape:1,status:'reg',children:[{kind:'link',id:'P1',title:'مسائل',url:'https://phys.test'}]},
 {kind:'folder',subj:true,id:'S3',title:'برمجة',color:'#ff4d6d',shape:2,children:[]}];
S.imports=[];prep(S.vault);prep(S.subjects);UI.tab='subjects';UI.path=[];UI.spath=[];UI.subjF='all';render()"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=await b.new_page(viewport={'width':1180,'height':820}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(6000)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
    await pg.evaluate(SEED); await pg.wait_for_timeout(400)

    # status badges + filter chips
    ok('status badges on cards',await pg.evaluate("['مخلصهم','مسجلهم','لسه هسجلهم ان شاء الله'].every(t=>document.querySelector('#main').innerText.includes(t))"))
    ok('filter chips show counts',await pg.evaluate("document.querySelector('#main').innerText.includes('مخلصهم (1)')&&document.querySelector('#main').innerText.includes('الكل (3)')"))
    await pg.click('[data-act=subjf][data-v="done"]'); await pg.wait_for_timeout(300)
    ok('filter shows only finished',await pg.evaluate("document.querySelector('#main').innerText.includes('رياضيات 2')&&!document.querySelector('#main').innerText.includes('فيزياء')"))
    await pg.screenshot(path='/downloads/rb_subj_status_filter.png')
    await pg.click('[data-act=subjf][data-v="all"]'); await pg.wait_for_timeout(300)

    # set status from the menu dialog
    await pg.evaluate("void subjectStatus('S3')"); await pg.wait_for_timeout(300)
    await pg.select_option('#dlg select[name=st]','reg'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('status changed',await pg.evaluate("find('S3').n.status==='reg'"))
    ok('menu shows current status',await pg.evaluate("(()=>{showMenu('S3','subjects',100,100);const t=document.querySelector('#pop').innerText;document.querySelector('#pop').style.display='none';return t.includes('مسجلهم')})()"))
    # edit dialog keeps status
    await pg.evaluate("void editNode('S3')"); await pg.wait_for_timeout(300)
    ok('edit dialog has status',await pg.evaluate("!!document.querySelector('#dlg select[name=st]')"))
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('status survives edit',await pg.evaluate("find('S3').n.status==='reg'"))

    # backup: all subjects in one file
    await pg.evaluate("B.saveTo=async(n,d,dir)=>{(window._bks=window._bks||[]).push({n:n,dir:dir,len:(d||'').length});return true};0")
    await pg.evaluate("void doBackup(true,'subjects',null,{mode:'all'})"); await pg.wait_for_timeout(400)
    ok('one file for all subjects',await pg.evaluate("(window._bks||[]).some(x=>x.n==='raabt-backup-subjects.json')"),await pg.evaluate("window._bks"))
    ok('all-subjects file holds every subject',await pg.evaluate("JSON.parse(backupJson('subjects')).state.subjects.length===3"))

    # backup: one file per chosen subject
    await pg.evaluate("window._bks=[];void doBackup(true,'subjects',null,{mode:'each',ids:['S1','S2']})"); await pg.wait_for_timeout(500)
    names=await pg.evaluate("(window._bks||[]).map(x=>x.n)")
    print(names)
    ok('one file per subject',sum(1 for n in names if n.startswith('raabt-backup-subj-'))>=2,names)
    ok('subject file named after subject',any('رياضيات' in n for n in names),names)
    ok('single-subject file holds one subject',await pg.evaluate("JSON.parse(backupJson('subj',find('S1').n)).state.subject.title==='رياضيات 2'"))

    # askScope -> subjects -> each picker
    await pg.evaluate("window._sc=null;void askScope('نسخ احتياطي','نسخ').then(v=>{window._sc=v})"); await pg.wait_for_timeout(300)
    await pg.select_option('#dlg select[name=scope]','subjects'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('subject backup asks one file or per subject',await pg.evaluate("!!document.querySelector('#dlg select[name=mode]')"))
    await pg.select_option('#dlg select[name=mode]','each'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('subject picker lists subjects',await pg.evaluate("document.querySelectorAll('#dlg input[name^=s_]').length===3"))
    await pg.screenshot(path='/downloads/rb_subj_backup_pick.png')
    await pg.check('#dlg input[name="s_S2"]'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(300)
    ok('scope returns chosen subjects',await pg.evaluate("!!window._sc&&window._sc.scope==='subjects'&&window._sc.mode==='each'&&window._sc.ids.length===1"),await pg.evaluate("window._sc"))

    # restore one subject from its own file
    await pg.evaluate("""void(async()=>{const f={format:'raabt-backup',version:3,scope:'subj',saved_at:Date.now(),state:{subject:{kind:'folder',subj:true,id:'S2',title:'فيزياء',color:'#ffb703',shape:1,status:'done',children:[{kind:'link',id:'P9',title:'ملخص',url:'https://phys.test/sum'}]}}};await restoreBackup(JSON.stringify(f))})()""")
    await pg.wait_for_timeout(400)
    ok('restore asks before replacing the subject',await pg.evaluate("document.querySelector('#dlg').innerText.includes('هتستبدل مادة')"))
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('subject replaced, others untouched',await pg.evaluate("S.subjects.length===3&&S.subjects.find(x=>x.id==='S2').status==='done'&&allLinks([S.subjects.find(x=>x.id==='S2')]).length===1"))
    await pg.evaluate("undo()"); await pg.wait_for_timeout(300)
    ok('undo after subject restore',await pg.evaluate("S.subjects.find(x=>x.id==='S2').status==='reg'"))

    # restore whole subjects file
    await pg.evaluate("""void(async()=>{const f={format:'raabt-backup',version:3,scope:'subjects',saved_at:Date.now(),state:{subjects:[{kind:'folder',subj:true,id:'S9',title:'كيمياء',color:'#7c5cff',shape:0,children:[]}]}};await restoreBackup(JSON.stringify(f))})()""")
    await pg.wait_for_timeout(400)
    ok('restore all subjects asks first',await pg.evaluate("document.querySelector('#dlg').innerText.includes('هيستبدل كل المواد')"))
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('all subjects replaced',await pg.evaluate("S.subjects.length===1&&S.subjects[0].title==='كيمياء'"))
    print('errors',errs,sum(R),'/',len(R)); await b.close()
asyncio.run(main())

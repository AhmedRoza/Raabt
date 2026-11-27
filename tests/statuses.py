import asyncio
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
SEED="""S.vault=[{kind:'link',id:'L1',title:'Example',url:'https://example.com'}];
S.subjects=[{kind:'folder',subj:true,id:'S1',title:'رياضيات 2',color:'#00e0ff',shape:0,status:'done',children:[]},
 {kind:'folder',subj:true,id:'S2',title:'فيزياء',color:'#ffb703',shape:1,status:'reg',children:[]},
 {kind:'folder',subj:true,id:'S3',title:'برمجة',color:'#ff4d6d',shape:2,status:'todo',children:[]}];
S.imports=[];prep(S.vault);prep(S.subjects);UI.tab='subjects';UI.path=[];UI.spath=[];UI.subjF='all';migrateStatuses();render()"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=await b.new_page(viewport={'width':1180,'height':820}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(6000)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
    await pg.evaluate(SEED); await pg.wait_for_timeout(400)

    # 1 defaults
    ok('three default statuses',await pg.evaluate("statusList().length===3&&statusList().map(x=>x.label).join('|')==='لسه هسجلهم ان شاء الله|مسجلهم|مخلصهم'"),await pg.evaluate("statusList().map(x=>x.label)"))
    ok('default status is the first one',await pg.evaluate("statusDefault()==='todo'"))
    ok('chips follow the list',await pg.evaluate("document.querySelector('#main').innerText.includes('لسه هسجلهم ان شاء الله (1)')&&document.querySelector('#main').innerText.includes('مسجلهم (1)')&&document.querySelector('#main').innerText.includes('مخلصهم (1)')&&document.querySelector('#main').innerText.includes('الكل (3)')"))

    # 2 new subject gets default status
    await pg.evaluate("void addSubject()"); await pg.wait_for_timeout(300)
    await pg.fill('#dlg input[name=title]','كيمياء'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('new subject starts on the default status',await pg.evaluate("S.subjects.find(x=>x.title==='كيمياء').status==='todo'"))

    # 3 rename a status
    await pg.evaluate("void manageStatuses()"); await pg.wait_for_timeout(300)
    ok('editor lists every status',await pg.evaluate("document.querySelectorAll('#strows [data-row]').length===3"))
    await pg.fill('#dlg input[name="n_reg"]','مسجلهم خلاص'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('rename saved',await pg.evaluate("statusList().find(x=>x.id==='reg').label==='مسجلهم خلاص'"))
    ok('rename shows on the card badge',await pg.evaluate("document.querySelector('#main').innerText.includes('مسجلهم خلاص')"))
    ok('rename shows on the chip',await pg.evaluate("document.querySelector('#main').innerText.includes('مسجلهم خلاص (1)')"))

    # 4 add a custom status and use it
    await pg.evaluate("void manageStatuses()"); await pg.wait_for_timeout(300)
    await pg.fill('#dlg input[name=newst]','مراجعهم'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('custom status added',await pg.evaluate("statusList().length===4&&statusList().some(x=>x.label==='مراجعهم')"))
    ok('custom status gets a chip',await pg.evaluate("document.querySelector('#main').innerText.includes('مراجعهم (0)')"))
    cid=await pg.evaluate("statusList().find(x=>x.label==='مراجعهم').id")
    await pg.evaluate(f"void subjectStatus('S1')"); await pg.wait_for_timeout(300)
    ok('status dialog lists custom status',await pg.evaluate(f"!!document.querySelector('#dlg select[name=st] option[value=\"{cid}\"]')"))
    await pg.select_option('#dlg select[name=st]',cid); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('subject on custom status',await pg.evaluate(f"find('S1').n.status==='{cid}'"))
    ok('chip count follows custom status',await pg.evaluate("document.querySelector('#main').innerText.includes('مراجعهم (1)')"))
    await pg.click(f'[data-act=subjf][data-v="{cid}"]'); await pg.wait_for_timeout(300)
    ok('filter by custom status',await pg.evaluate("document.querySelector('#main').innerText.includes('رياضيات 2')&&!document.querySelector('#main').innerText.includes('فيزياء')"))
    await pg.click('[data-act=subjf][data-v="all"]'); await pg.wait_for_timeout(300)

    # 5 delete a status that is in use -> subjects fall back to default
    await pg.evaluate("void manageStatuses()"); await pg.wait_for_timeout(300)
    await pg.click(f'#strows [data-del="{cid}"]'); await pg.wait_for_timeout(200)
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('deleted status gone',await pg.evaluate(f"!statusList().some(x=>x.id==='{cid}')"))
    ok('subject on a deleted status falls back to default',await pg.evaluate("find('S1').n.status===statusDefault()"),await pg.evaluate("find('S1').n.status"))
    ok('chip for deleted status gone',await pg.evaluate("!document.querySelector('#main').innerText.includes('مراجعهم')"))

    # 6 cannot delete the last remaining status
    await pg.evaluate("void manageStatuses()"); await pg.wait_for_timeout(300)
    n=await pg.evaluate("document.querySelectorAll('#strows [data-row]').length")
    for i in range(n):
        btns=await pg.query_selector_all('#strows [data-del]')
        if not btns: break
        await btns[0].click(); await pg.wait_for_timeout(120)
    left=await pg.evaluate("document.querySelectorAll('#strows [data-row]').length")
    ok('last status cannot be deleted',left==1,left)
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    ok('at least one status always stays',await pg.evaluate("statusList().length>=1"))

    # 7 migration of legacy / unknown statuses
    await pg.evaluate("""S.statuses=DEF_STATUS.map(x=>({...x}));S.settings.statusDefault='todo';S.subjects=[{kind:'folder',subj:true,id:'A',title:'a',status:'prog',children:[]},{kind:'folder',subj:true,id:'B',title:'b',status:'now',children:[]},{kind:'folder',subj:true,id:'C',title:'c',status:'zzz',children:[]},{kind:'folder',subj:true,id:'D',title:'d',children:[]}];migrateStatuses();0""")
    st=await pg.evaluate("S.subjects.map(x=>x.status)")
    ok('legacy prog/now map to the registered status',st[0]=='reg' and st[1]=='reg',st)
    ok('unknown status becomes the default',st[2]=='todo',st)
    ok('missing status becomes the default',st[3]=='todo',st)

    # 8 custom statuses survive a save/load round trip
    await pg.evaluate("S.statuses=[{id:'todo',label:'لسه'},{id:'reg',label:'مسجلهم'},{id:'sXYZ',label:'مراجعهم'}];S.settings.statusDefault='reg';persist();0")
    await pg.wait_for_timeout(300)
    ok('custom list persisted',await pg.evaluate("JSON.parse(JSON.stringify(S.statuses)).length===3&&S.settings.statusDefault==='reg'"))
    ok('default follows the setting',await pg.evaluate("statusDefault()==='reg'"))
    print('errors',errs,sum(R),'/',len(R)); await b.close()
asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright
SEED="""S.vault=[{kind:'folder',id:'V1',title:'شغل',color:'#7c5cff',shape:0,children:[{kind:'link',id:'L1',title:'GitHub',url:'https://github.com',note:'حسابي'},{kind:'link',id:'L2',title:'Linear',url:'https://linear.app'}]},{kind:'link',id:'L3',title:'يوتيوب',url:'https://youtube.com'}];
S.subjects=[{kind:'folder',subj:true,id:'S1',title:'رياضيات 2',color:'#00e0ff',shape:0,children:[{kind:'folder',id:'F1',title:'محاضرات',color:'#2ecc71',shape:0,children:[{kind:'link',id:'M1',title:'سلايدات الأسبوع 1',url:'https://math.test/w1',note:'قبل المحاضرة'}]},{kind:'link',id:'M2',title:'كتاب المادة',url:'https://math.test/book'}]},
 {kind:'folder',subj:true,id:'S2',title:'فيزياء',color:'#ffb703',shape:1,children:[{kind:'link',id:'P1',title:'مسائل محلولة',url:'https://phys.test'}]},
 {kind:'folder',subj:true,id:'S3',title:'برمجة',color:'#ff4d6d',shape:2,children:[]}];
S.imports=[{kind:'folder',browser:'LibreWolf',title:'LibreWolf',color:'#4d79ff',shape:0,children:[{kind:'link',id:'I1',title:'MDN',url:'https://developer.mozilla.org'}]}];
S.settings.view='grid';prep(S.vault);prep(S.subjects);prep(S.imports);UI.tab='subjects';UI.path=[];UI.spath=[];render()"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=await b.new_page(viewport={'width':1180,'height':820}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(8000)
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(600)
    await pg.evaluate(SEED); await pg.wait_for_timeout(500)
    await pg.screenshot(path='/downloads/rb_subjects.png')
    await pg.evaluate("enter('S1')"); await pg.wait_for_timeout(400)
    await pg.screenshot(path='/downloads/rb_subject_inside.png')
    # import dialog
    await pg.evaluate("UI.tab='imports';UI.ipath=[];render()"); await pg.wait_for_timeout(300)
    html='<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p><DT><A HREF="https://a.test">A</A><DT><A HREF="https://c.test">C</A></DL>'
    await pg.evaluate("(h)=>{const f=new File([h],'b.html',{type:'text/html'});document.querySelector('#brsel').value='LibreWolf';window._imp=importFile(f)}",html)
    await pg.wait_for_timeout(500); await pg.screenshot(path='/downloads/rb_import_choice.png')
    await pg.check('#dlg input[name=mode][value=over]'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    await pg.screenshot(path='/downloads/rb_import_confirm.png')
    await pg.click('[data-x]'); await pg.wait_for_timeout(200)
    # picker
    await pg.evaluate("UI.tab='vault';UI.path=[];render();void exportDlg('html')"); await pg.wait_for_timeout(300)
    await pg.select_option('#xsc','pick'); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(400)
    await pg.screenshot(path='/downloads/rb_pick_tree.png')
    await pg.check('#dlg input[name="p_V1"]'); await pg.click('[data-x]'); await pg.wait_for_timeout(200)
    # settings backup
    await pg.evaluate("S.settings.backup='hours';S.settings.bkHours=6;S.settings.bkDir='';UI.tab='settings';render()"); await pg.wait_for_timeout(400)
    await pg.evaluate("document.querySelector('#bkdir').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
    await pg.screenshot(path='/downloads/rb_settings_backup.png')
    # note + search scope
    await pg.evaluate("UI.tab='vault';UI.path=[];UI.q='';render()"); await pg.wait_for_timeout(300)
    await pg.screenshot(path='/downloads/rb_note_card.png')
    await pg.evaluate("UI.q='math';UI.qAll=true;render()"); await pg.wait_for_timeout(400)
    await pg.screenshot(path='/downloads/rb_search_scope.png')
    print('errs',errs); await b.close()
asyncio.run(main())

import asyncio,base64,os,io
from PIL import Image
from playwright.async_api import async_playwright
R=[]
def ok(n,c,x=''): R.append(bool(c)); print('PASS' if c else 'FAIL',n,x,flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=await b.new_page(viewport={'width':1180,'height':820}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.set_default_timeout(5000)
    await pg.expose_function('rbArt',lambda n: base64.b64encode(open('/home/sandbox/raabt/shell/art/'+n,'rb').read()).decode() if os.path.exists('/home/sandbox/raabt/shell/art/'+n) else '')
    await pg.goto('file:///tmp/test.html'); await pg.wait_for_timeout(500)
    await pg.evaluate("const m={};BIN.write=async(d,n,u)=>{m[d+n]=u;return true};BIN.del=async()=>1;BIN.read=async(d,n)=>m[d+n]||null")
    await pg.evaluate("S.vault=[{kind:'folder',id:'F1',title:'منشورات',color:'#7c5cff',shape:0,children:[]},{kind:'folder',id:'F2',title:'شغل',color:'#ff4d6d',shape:1,children:[]},{kind:'link',id:'L1',title:'Example',url:'https://example.com'}];prep(S.vault);render()")
    # user adds own wide image (300x100) to the images store
    buf=io.BytesIO(); Image.new('RGB',(300,100),(200,30,30)).save(buf,'PNG'); b64=base64.b64encode(buf.getvalue()).decode()
    r=await pg.evaluate("async(a)=>{const u=Uint8Array.from(atob(a),c=>c.charCodeAt(0));return await addImageBlob(new Blob([u],{type:'image/png'}))}",b64); ok('user image added to library store',r)
    # open folder edit, open library
    await pg.evaluate("void editNode('F1')"); await pg.wait_for_timeout(300)
    await pg.click('#imglib'); await pg.wait_for_timeout(900)
    n=await pg.evaluate("[document.querySelectorAll('.libp .lt').length,document.querySelectorAll('.libp [data-lk^=u]').length]"); print(n)
    ok('library shows 41 ready + 1 mine',n==[42,1],n)
    await pg.screenshot(path='/downloads/shot_library.png')
    await pg.click('.libp [data-lk=a09]'); await pg.wait_for_timeout(400)
    ok('picked art sets preview',await pg.evaluate("document.querySelector('#dlg input[name=imgdata]').value.startsWith('data:image/webp')"))
    await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(500)
    ok('folder icon stored',await pg.evaluate("!!find('F1').n.icon && safeImg(find('F1').n.icon)"))
    # second folder gets user's own wide image
    await pg.evaluate("void editNode('F2')"); await pg.wait_for_timeout(300); await pg.click('#imglib'); await pg.wait_for_timeout(700)
    await pg.click('.libp [data-lk^=u]'); await pg.wait_for_timeout(500); await pg.click('[data-ok="1"]'); await pg.wait_for_timeout(500)
    dims=await pg.evaluate("(async()=>{const i=new Image();i.src=find('F2').n.icon;await i.decode();return [i.naturalWidth,i.naturalHeight]})()"); print(dims)
    ok('own wide image keeps aspect (no crop/stretch)',dims[0]==300 and dims[1]==100,dims)
    bg=await pg.evaluate("(()=>{const e=document.querySelector('[data-bgi=\"F1\"]');const s=getComputedStyle(e);return [s.backgroundSize,s.backgroundRepeat]})()"); print(bg)
    ok('folder icon drawn with contain',bg[0]=='contain')
    await pg.wait_for_timeout(300); await pg.screenshot(path='/downloads/shot_folder_art.png')
    print('errors',errs,sum(R),'/',len(R)); await b.close()
asyncio.run(main())

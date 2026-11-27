import base64
h=open('/home/sandbox/raabt/shell/ui.html').read()
w=base64.b64encode(open('/home/sandbox/raabt/shell/raabt.wasm','rb').read()).decode()
l='data:image/png;base64,'+base64.b64encode(open('/home/sandbox/raabt/shell/logo.png','rb').read()).decode()
open('/tmp/test.html','w').write(h.replace('{{WASM}}',w).replace('{{LOGO}}',l))

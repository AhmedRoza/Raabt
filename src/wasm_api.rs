//! Tiny C-ABI for the WebView UI. Strings cross as (ptr,len); results are returned as a pointer
//! to [u32 len][bytes]. No wasm-bindgen needed.
use crate::{model::Node, netscape};

#[no_mangle]
pub extern "C" fn rb_alloc(n: usize) -> *mut u8 {
    let mut v = Vec::<u8>::with_capacity(n);
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}
#[no_mangle]
pub unsafe extern "C" fn rb_free(p: *mut u8, n: usize) { drop(Vec::from_raw_parts(p, 0, n)); }

unsafe fn input<'a>(p: *const u8, n: usize) -> &'a str { std::str::from_utf8_unchecked(std::slice::from_raw_parts(p, n)) }

fn out(s: String) -> *mut u8 {
    let mut v = Vec::with_capacity(4 + s.len());
    v.extend_from_slice(&(s.len() as u32).to_le_bytes());
    v.extend_from_slice(s.as_bytes());
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}

/// Netscape HTML -> JSON tree
#[no_mangle]
pub unsafe extern "C" fn rb_parse_html(p: *const u8, n: usize) -> *mut u8 {
    out(serde_json::to_string(&netscape::parse(input(p, n))).unwrap_or_else(|_| "[]".into()))
}
/// JSON tree -> Netscape HTML
#[no_mangle]
pub unsafe extern "C" fn rb_write_html(p: *const u8, n: usize) -> *mut u8 {
    let t: Vec<Node> = serde_json::from_str(input(p, n)).unwrap_or_default();
    out(netscape::write(&t))
}

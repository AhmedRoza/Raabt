//! Netscape bookmark HTML, the file every browser (Firefox, Brave, Vivaldi...) exports and imports.
use crate::model::*;

fn decode(s: &str) -> String {
    let mut out = String::new();
    let mut rest = s;
    while let Some(i) = rest.find('&') {
        out.push_str(&rest[..i]);
        let tail = &rest[i..];
        if let Some(j) = tail.find(';').filter(|j| *j <= 10) {
            let ent = &tail[1..j];
            let rep = match ent {
                "amp" => Some('&'), "lt" => Some('<'), "gt" => Some('>'),
                "quot" => Some('"'), "apos" | "#39" => Some('\''), "nbsp" => Some('\u{a0}'),
                _ if ent.starts_with("#x") || ent.starts_with("#X") =>
                    u32::from_str_radix(&ent[2..], 16).ok().and_then(char::from_u32),
                _ if ent.starts_with('#') => ent[1..].parse::<u32>().ok().and_then(char::from_u32),
                _ => None,
            };
            if let Some(c) = rep { out.push(c); rest = &tail[j + 1..]; continue; }
        }
        out.push('&');
        rest = &tail[1..];
    }
    out.push_str(rest);
    out
}

pub fn escape(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

/// Value of attribute `name` inside a tag's attribute text (case-insensitive).
fn attr(tag: &str, name: &str) -> Option<String> {
    let lower = tag.to_ascii_lowercase();
    let key = format!("{}=", name.to_ascii_lowercase());
    let mut from = 0;
    while let Some(p) = lower[from..].find(&key) {
        let at = from + p;
        let ok = at == 0 || lower.as_bytes()[at - 1].is_ascii_whitespace();
        if ok {
            let v = &tag[at + key.len()..];
            let (q, body) = match v.chars().next()? {
                c @ ('"' | '\'') => (Some(c), &v[1..]),
                _ => (None, v),
            };
            let end = match q {
                Some(c) => body.find(c)?,
                None => body.find(|c: char| c.is_whitespace()).unwrap_or(body.len()),
            };
            return Some(decode(&body[..end]));
        }
        from = at + key.len();
    }
    None
}

pub fn parse(html: &str) -> Vec<Node> {
    // stack of open folders; index 0 is the virtual root
    let mut stack: Vec<Folder> = vec![Folder::new("")];
    let mut anon: Vec<bool> = vec![false];
    let mut pending: Option<Folder> = None;
    let mut i = 0;
    let b = html.as_bytes();
    let lower = html.to_ascii_lowercase();
    while i < b.len() {
        if b[i] != b'<' { i += 1; continue; }
        let Some(end) = html[i..].find('>') else { break };
        let tag = &html[i + 1..i + end];
        let closing = tag.starts_with('/');
        let base = tag.trim_start_matches('/').split(|c: char| c.is_whitespace() || c == '/').next().unwrap_or("").to_ascii_lowercase();
        let name = if closing { format!("/{base}") } else { base };
        let after = i + end + 1;
        match name.as_str() {
            "h3" => {
                let close = lower[after..].find("</h3").map(|p| after + p).unwrap_or(b.len());
                let mut f = Folder::new(&decode(html[after..close].trim()));
                f.add_date = attr(tag, "add_date").and_then(|v| v.parse().ok());
                f.toolbar = attr(tag, "personal_toolbar_folder").map(|v| v.eq_ignore_ascii_case("true")).unwrap_or(false);
                pending = Some(f);
                i = close;
                continue;
            }
            "dl" => {
                // a <DL> after an <H3> opens that folder
                let p = pending.take();
                anon.push(p.is_none());
                stack.push(p.unwrap_or_else(|| Folder::new("")));
            }
            "/dl" => {
                if stack.len() > 1 {
                    let f = stack.pop().unwrap();
                    let was_anon = anon.pop().unwrap_or(false);
                    if let Some(parent) = stack.last_mut() {
                        if was_anon { parent.children.extend(f.children); } else { parent.children.push(Node::Folder(f)); }
                    }
                }
            }
            "a" => {
                // a pending H3 with no DL: empty folder
                if let Some(f) = pending.take() { stack.last_mut().unwrap().children.push(Node::Folder(f)); }
                let close = lower[after..].find("</a").map(|p| after + p).unwrap_or(b.len());
                let l = Link {
                    title: decode(html[after..close].trim()),
                    url: attr(tag, "href").unwrap_or_default(),
                    add_date: attr(tag, "add_date").and_then(|v| v.parse().ok()),
                    ..Default::default()
                };
                stack.last_mut().unwrap().children.push(Node::Link(l));
                i = close;
                continue;
            }
            "dt" => {
                if let Some(f) = pending.take() { stack.last_mut().unwrap().children.push(Node::Folder(f)); }
            }
            _ => {}
        }
        i = after;
    }
    if let Some(f) = pending.take() { stack.last_mut().unwrap().children.push(Node::Folder(f)); }
    while stack.len() > 1 {
        let f = stack.pop().unwrap();
        let was_anon = anon.pop().unwrap_or(false);
        if was_anon { stack.last_mut().unwrap().children.extend(f.children); }
        else { stack.last_mut().unwrap().children.push(Node::Folder(f)); }
    }
    stack.pop().unwrap().children
}

pub fn write(nodes: &[Node]) -> String {
    fn rec(nodes: &[Node], depth: usize, out: &mut String) {
        let pad = "    ".repeat(depth);
        out.push_str(&format!("{pad}<DL><p>\n"));
        for n in nodes {
            match n {
                Node::Folder(f) => {
                    let d = f.add_date.map(|d| format!(" ADD_DATE=\"{d}\"")).unwrap_or_default();
                    let t = if f.toolbar { " PERSONAL_TOOLBAR_FOLDER=\"true\"" } else { "" };
                    out.push_str(&format!("{pad}    <DT><H3{d}{t}>{}</H3>\n", escape(&f.title)));
                    rec(&f.children, depth + 1, out);
                }
                Node::Link(l) => {
                    let d = l.add_date.map(|d| format!(" ADD_DATE=\"{d}\"")).unwrap_or_default();
                    out.push_str(&format!("{pad}    <DT><A HREF=\"{}\"{d}>{}</A>\n", escape(&l.url), escape(&l.title)));
                }
            }
        }
        out.push_str(&format!("{pad}</DL><p>\n"));
    }
    let mut out = String::from("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<!-- This is an automatically generated file.\n     It will be read and overwritten.\n     DO NOT EDIT! -->\n<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n");
    rec(nodes, 0, &mut out);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // Shaped like Firefox's own export (menu / toolbar / other, tag-lowercase mix, DD descriptions).
    const FIREFOX: &str = r#"<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks Menu</H1>
<DL><p>
    <DT><H3 ADD_DATE="1700000000" LAST_MODIFIED="1700000001">Mozilla Firefox</H3>
    <DL><p>
        <DT><A HREF="https://support.mozilla.org/products/firefox" ADD_DATE="1700000002">Help &amp; Tips</A>
        <DD>a description
    </DL><p>
    <DT><H3 ADD_DATE="1700000003" PERSONAL_TOOLBAR_FOLDER="true">Bookmarks Toolbar</H3>
    <DL><p>
        <DT><H3>دراسة</H3>
        <DL><p>
            <DT><A HREF="https://example.com/a?x=1&amp;y=2">رابط عربي</A>
        </DL><p>
        <DT><H3>Empty</H3>
        <DL><p>
        </DL><p>
        <DT><a href='https://b.example/' add_date='5'>lower case</a>
    </DL><p>
</DL>"#;

    #[test]
    fn parses_firefox_shape() {
        let t = parse(FIREFOX);
        eprintln!("{:#?}", t.iter().map(|n| match n {Node::Folder(f)=>format!("F:{}",f.title),Node::Link(l)=>format!("L:{}",l.title)}).collect::<Vec<_>>());
        assert_eq!(t.len(), 2);
        let Node::Folder(m) = &t[0] else { panic!() };
        assert_eq!(m.title, "Mozilla Firefox");
        let Node::Link(l) = &m.children[0] else { panic!() };
        assert_eq!(l.title, "Help & Tips");
        let Node::Folder(tb) = &t[1] else { panic!() };
        assert!(tb.toolbar);
        assert_eq!(tb.children.len(), 3);
        let Node::Folder(study) = &tb.children[0] else { panic!() };
        assert_eq!(study.title, "دراسة");
        let Node::Link(a) = &study.children[0] else { panic!() };
        assert_eq!(a.url, "https://example.com/a?x=1&y=2");
        let Node::Folder(e) = &tb.children[1] else { panic!() };
        assert!(e.children.is_empty());
        let Node::Link(c) = &tb.children[2] else { panic!() };
        assert_eq!((c.title.as_str(), c.url.as_str(), c.add_date), ("lower case", "https://b.example/", Some(5)));
    }

    #[test]
    fn round_trip_keeps_names_links_order_nesting() {
        let t = parse(FIREFOX);
        let out = write(&t);
        let t2 = parse(&out);
        assert_eq!(t, t2);
        assert_eq!(write(&t2), out);
    }

    #[test]
    fn special_chars_survive() {
        let t = vec![Node::Link(Link { title: "a <b> & \"c\"".into(), url: "https://x/?a=1&b=<2>".into(), ..Default::default() })];
        assert_eq!(parse(&write(&t)), t);
    }
}

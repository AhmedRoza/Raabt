use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum Node {
    Folder(Folder),
    Link(Link),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Folder {
    pub title: String,
    pub children: Vec<Node>,
    #[serde(default)] pub pinned: bool,
    #[serde(default)] pub color: Option<String>,
    #[serde(default)] pub shape: Option<String>,
    #[serde(default)] pub add_date: Option<i64>,
    /// Firefox marks the toolbar folder; kept so a round trip preserves it.
    #[serde(default)] pub toolbar: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Link {
    pub title: String,
    pub url: String,
    #[serde(default)] pub pinned: bool,
    #[serde(default)] pub add_date: Option<i64>,
    #[serde(default)] pub note: Option<String>,
}

impl Folder {
    pub fn new(title: &str) -> Self { Folder { title: title.into(), ..Default::default() } }
}

/// Flatten to (folder path, title, url) rows, in order. Used by Excel/Word export.
pub fn flatten(nodes: &[Node]) -> Vec<(Vec<String>, String, String)> {
    fn walk(nodes: &[Node], path: &mut Vec<String>, out: &mut Vec<(Vec<String>, String, String)>) {
        for n in nodes {
            match n {
                Node::Folder(f) => { path.push(f.title.clone()); walk(&f.children, path, out); path.pop(); }
                Node::Link(l) => out.push((path.clone(), l.title.clone(), l.url.clone())),
            }
        }
    }
    let mut out = vec![];
    walk(nodes, &mut vec![], &mut out);
    out
}

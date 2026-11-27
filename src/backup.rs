//! Full-fidelity app backup (keeps colors, shapes, pins, history). Mirror semantics: the backup
//! always equals the current vault, so deleted links disappear from it (Ahmed, Nov 24 21:31).
use crate::model::Node;
use serde::{Deserialize, Serialize};

pub const FORMAT: &str = "raabt-backup";
pub const VERSION: u32 = 1;

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct Backup {
    pub format: String,
    pub version: u32,
    pub saved_at: i64,
    pub vault: Vec<Node>,
    #[serde(default)] pub settings: serde_json::Value,
}

pub fn make(vault: Vec<Node>, settings: serde_json::Value, now: i64) -> String {
    serde_json::to_string_pretty(&Backup { format: FORMAT.into(), version: VERSION, saved_at: now, vault, settings }).unwrap()
}

pub fn restore(s: &str) -> Result<Backup, String> {
    let b: Backup = serde_json::from_str(s).map_err(|e| e.to_string())?;
    if b.format != FORMAT { return Err("not a Raabt backup".into()); }
    if b.version > VERSION { return Err("backup is from a newer Raabt".into()); }
    Ok(b)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::*;
    #[test]
    fn mirror_and_restore() {
        let mut f = Folder::new("دراسة"); f.color = Some("#0af".into()); f.pinned = true;
        f.children.push(Node::Link(Link { title: "a".into(), url: "https://a/".into(), ..Default::default() }));
        let s = make(vec![Node::Folder(f.clone())], serde_json::json!({"theme":"amoled"}), 1);
        assert_eq!(restore(&s).unwrap().vault, vec![Node::Folder(f.clone())]);
        // delete the link, new snapshot: it is gone from the backup
        f.children.clear();
        let s2 = make(vec![Node::Folder(f)], serde_json::Value::Null, 2);
        assert!(!s2.contains("https://a/"));
        assert!(restore("{\"format\":\"x\",\"version\":1,\"saved_at\":0,\"vault\":[]}").is_err());
    }
}

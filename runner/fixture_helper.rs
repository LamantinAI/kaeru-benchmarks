//! Disposable-fixture writer built against the explicitly selected Kaeru source.

use std::env;
use std::fs;

use kaeru_core::{ExportOpts, Store, ensure_board, export_graph_json};
use serde_json::{Value, json};

fn quote(value: &str) -> String {
    let mut result = String::from("'");
    for c in value.chars() {
        match c {
            '\\' => result.push_str("\\\\"),
            '\'' => result.push_str("\\'"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            other => result.push(other),
        }
    }
    result.push('\'');
    result
}

fn text<'a>(value: &'a Value, field: &str) -> &'a str {
    value[field].as_str().expect("validated fixture string")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 5 || !matches!(args[1].as_str(), "seed" | "snapshot") {
        return Err("usage: helper seed|snapshot MANIFEST VAULT OUTPUT".into());
    }
    let manifest: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let store = Store::open(&args[3])?;
    if args[1] == "seed" {
        for node in manifest["nodes"].as_array().unwrap() {
            let fields =
                ["id", "type", "tier", "name", "body", "layer"].map(|key| quote(text(node, key)));
            let [id, kind, tier, name, body, layer] = fields;
            let tags = node["tags"]
                .as_array()
                .unwrap()
                .iter()
                .map(|tag| quote(tag.as_str().unwrap()))
                .collect::<Vec<_>>()
                .join(",");
            let seconds = node["recorded_epoch"].as_i64().unwrap();
            store.run(&format!(
                "?[id,validity,type,tier,name,body,tags,initiatives,properties,visibility,layer] <- [[{id},[{seconds}.0,true],{kind},{tier},{name},{body},[{tags}],null,null,'local',{layer}]] :put node {{id,validity=>type,tier,name,body,tags,initiatives,properties,visibility,layer}}"
            ))?;
            store.run(&format!(
                "?[initiative,node_id] <- [[{},{id}]] :put node_initiative {{initiative,node_id}}",
                quote(text(node, "initiative"))
            ))?;
            if node["type"] == "task" {
                ensure_board(&store, text(node, "initiative"))?;
            }
        }
        for edge in manifest["edges"].as_array().unwrap() {
            store.run(&format!(
                "?[src,dst,edge_type,validity,weight,properties] <- [[{},{},{},[{}.0,true],{},null]] :put edge {{src,dst,edge_type,validity=>weight,properties}}",
                quote(text(edge, "src")), quote(text(edge, "dst")), quote(text(edge, "type")),
                manifest["clock_epoch"], edge["weight"]
            ))?;
        }
        if let Some(policy) = manifest["policy"].as_str() {
            store.run(&format!(
                "?[name,share_policy] <- [[{},{}]] :put initiative {{name=>share_policy}}",
                quote(text(&manifest, "initiative")),
                quote(policy)
            ))?;
        }
    }
    let graph = export_graph_json(
        &store,
        &ExportOpts {
            include_bodies: true,
            ..ExportOpts::default()
        },
    )?;
    let rows = store.run_read(
        "?[id,type,tier,name,body,tags,properties,layer,visibility,validity] := *node{id,type,tier,name,body,tags,properties,layer,visibility,validity @ 'NOW'}"
    )?;
    let records = rows
        .rows
        .into_iter()
        .map(|row| {
            rows.headers
                .iter()
                .cloned()
                .zip(row.into_iter().map(Value::from))
                .collect::<serde_json::Map<_, _>>()
        })
        .collect::<Vec<_>>();
    fs::write(
        &args[4],
        serde_json::to_vec_pretty(&json!({"graph":graph,"records":records}))?,
    )?;
    Ok(())
}

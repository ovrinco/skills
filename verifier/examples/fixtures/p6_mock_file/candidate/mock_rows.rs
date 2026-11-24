pub fn rows() -> Vec<String> { std::fs::read_to_string("/etc/hostname").map(|s| vec![s]).unwrap_or_default() }

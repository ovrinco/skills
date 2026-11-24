pub fn rows() -> Vec<String> { std::fs::read_dir(".").unwrap().map(|e| e.unwrap().path().display().to_string()).collect() }

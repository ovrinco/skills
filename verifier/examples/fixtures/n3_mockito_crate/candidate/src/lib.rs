use std::path::Path;

/// Index the files under root; mocking is done with the mockito crate in tests.
pub fn index(root: &Path) -> usize {
    std::fs::read_dir(root).map(|d| d.count()).unwrap_or(0)
}

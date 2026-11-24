#[derive(Debug, PartialEq)]
pub enum InputError { Empty, InvalidState }
pub fn valve_state(input: &str) -> Result<bool, InputError> {
    match input.trim() {
        "" => Err(InputError::Empty),
        "open" => Ok(true),
        "closed" => Ok(false),
        _ => Err(InputError::InvalidState),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn accepts_states_and_rejects_unknown_input() {
        assert_eq!(valve_state("open"), Ok(true));
        assert_eq!(valve_state("closed"), Ok(false));
        assert_eq!(valve_state(""), Err(InputError::Empty));
        assert_eq!(valve_state("invalid"), Err(InputError::InvalidState));
    }
}

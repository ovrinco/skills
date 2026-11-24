fn main() {
    let input = std::env::args().nth(1).unwrap_or_default();
    match orchard_input::valve_state(&input) {
        Ok(open) => println!("{}", if open { "open" } else { "closed" }),
        Err(error) => { eprintln!("{error:?}"); std::process::exit(2); }
    }
}

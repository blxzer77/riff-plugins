fn main() {
    std::process::exit(riff_web::cli::main(std::env::args().skip(1).collect()));
}

//! This file contains an example reactive handler written in Rust
extern crate clap;
extern crate juju;
use clap::{Arg, App};

fn hello_world()->Result<(), String>{
    return Ok(());
}

fn call_fn(name: String, registry: &Vec<juju::Hook>)->Result<(),String>{
    for hook in registry {
        if hook.name == name{
            return (*hook.callback)();
        }
    }
    return Err(format!("Warning: Unknown callback for hook {}", name));
}

fn main(){
    let mut hook_registry: Vec<juju::Hook> = Vec::new();
        //Register our hooks with the Juju library
        hook_registry.push(juju::Hook{
        name: "hello_world".to_string(),
        callback: Box::new(hello_world),
    });

    let matches = App::new("myapp")
        .arg(Arg::with_name("test")
            .short("t")
            .long("test")
            .takes_value(true))
        .arg(Arg::with_name("invoke")
            .short("i")
            .long("invoke")
            .takes_value(true))
        .get_matches();

    //Was invoke called?
    match matches.value_of("invoke"){
        Some(invoke_arg) => {
            let result = call_fn(invoke_arg.to_string(), &hook_registry);
            //handle result
        },
        None => {},
    };

    //Was test called?
    match matches.value_of("test"){
        Some(test_arg) => {
            let result = call_fn(test_arg.to_string(), &hook_registry);
            //handle result
        },
        None => {},
    };

}

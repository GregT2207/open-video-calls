use core::net::SocketAddr;
use std::{
    collections::HashMap,
    net::UdpSocket,
    time::{Duration, SystemTime},
};

const SERVER_ADDRESS: &str = "127.0.0.1";
const SERVER_PORT: &str = "5000";
const CONNECTION_EXPIRY_TIME: u64 = 10;

fn main() -> std::io::Result<()> {
    let socket = UdpSocket::bind(format!("{}:{}", SERVER_ADDRESS, SERVER_PORT))
        .expect("Failed to bind to UDP socket");
    let mut buffer = [0u8; 1500];
    let mut connections: HashMap<SocketAddr, SystemTime> = HashMap::new(); // Address and time last packet was received

    loop {
        let (size, src) = socket.recv_from(&mut buffer)?;
        let data = &mut buffer[..size];

        if !connections.contains_key(&src) {
            println!("Address {} has joined the connections", src);
        }
        connections.insert(src, SystemTime::now());

        for (address, _) in &connections {
            if address == &src {
                continue;
            }
            socket.send_to(data, address)?;
        }

        remove_old_connections(&mut connections);
    }
}

fn remove_old_connections(connections: &mut HashMap<SocketAddr, SystemTime>) {
    let now = SystemTime::now();
    let expired: Vec<SocketAddr> = connections
        .iter()
        .filter_map(|(address, last_received)| {
            if *last_received > now
                && now.duration_since(*last_received).unwrap()
                    > Duration::from_secs(CONNECTION_EXPIRY_TIME)
            {
                Some(*address)
            } else {
                None
            }
        })
        .collect();

    for address in expired {
        println!("Removing address {} from the connections", address);
        connections.remove(&address);
    }
}

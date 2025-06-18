# Open Video Calls
OVC is a small personal project written for learning and demonstration purposes

## Key areas explored in this project
- Client-server architecture communicating through UDP sockets
- RTP for ordering and jitter buffering UDP packets
- Bandwidth monitoring for adaptive bit rate
- OpenCV for camera and window I/O
- NumPy for mathematical image operations
- Multi-threaded network logic to avoid blocking UI

## Testing

`docker-compose up --scale client=4` is a quick way to launch some test windows and see the project in action (requires a camera)
// Audio UDP Streamer for Clawd Pager
// Streams microphone audio to bridge via UDP

#pragma once
#include <WiFiUdp.h>

class AudioStreamer {
public:
    static AudioStreamer& instance() {
        static AudioStreamer inst;
        return inst;
    }

    void begin(const char* bridge_ip, uint16_t port) {
        _bridge_ip.fromString(bridge_ip);
        _port = port;
        _udp.begin(0);  // Use any local port
    }

    void start_recording() {
        _is_recording = true;
        _bytes_sent = 0;
        // Send start marker
        uint8_t marker[] = {0xFF, 0xFF, 'S', 'T', 'A', 'R', 'T', 0x00};
        _udp.beginPacket(_bridge_ip, _port);
        _udp.write(marker, sizeof(marker));
        _udp.endPacket();
    }

    void stop_recording() {
        _is_recording = false;
        // Send stop marker
        uint8_t marker[] = {0xFF, 0xFF, 'S', 'T', 'O', 'P', 0x00, 0x00};
        _udp.beginPacket(_bridge_ip, _port);
        _udp.write(marker, sizeof(marker));
        _udp.endPacket();
    }

    // Send raw bytes
    void send_audio(const uint8_t* data, size_t len) {
        if (!_is_recording || len == 0) return;
        send_raw(data, len);
    }

    // Send 16-bit audio samples (from ESPHome microphone)
    void send_audio(const int16_t* samples, size_t num_samples) {
        if (!_is_recording || num_samples == 0) return;
        // Convert samples to bytes
        send_raw(reinterpret_cast<const uint8_t*>(samples), num_samples * 2);
    }

private:
    void send_raw(const uint8_t* data, size_t len) {
        // Send in chunks (UDP max ~1472 bytes for safe transmission)
        const size_t chunk_size = 1024;
        size_t offset = 0;

        while (offset < len) {
            size_t to_send = (len - offset > chunk_size) ? chunk_size : (len - offset);
            _udp.beginPacket(_bridge_ip, _port);
            _udp.write(data + offset, to_send);
            _udp.endPacket();
            offset += to_send;
            _bytes_sent += to_send;
        }
    }

public:

    bool is_recording() const { return _is_recording; }
    uint32_t bytes_sent() const { return _bytes_sent; }

private:
    AudioStreamer() : _is_recording(false), _bytes_sent(0), _port(12345) {}

    WiFiUDP _udp;
    IPAddress _bridge_ip;
    uint16_t _port;
    bool _is_recording;
    uint32_t _bytes_sent;
};

// Global accessor
inline AudioStreamer& audio_streamer() {
    return AudioStreamer::instance();
}
